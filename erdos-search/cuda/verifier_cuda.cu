#include <iostream>
#include <vector>
#include <string>
#include <sstream>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cuda_runtime.h>
#include <thrust/device_ptr.h>
#include <thrust/sort.h>

#define BOHMAN_CONSTANT 0.22002

__constant__ uint64_t d_const_elements[64];

// Kernel to compute 2^n subset sums in parallel
__global__ void generate_subset_sums_kernel(uint64_t* sums, uint64_t total_subsets, int n) {
    uint64_t idx = blockIdx.x * (uint64_t)blockDim.x + threadIdx.x;
    if (idx < total_subsets) {
        uint64_t sum = 0;
        #pragma unroll
        for (int j = 0; j < 32; ++j) {
            if (j >= n) break;
            if ((idx >> j) & 1ULL) {
                sum += d_const_elements[j];
            }
        }
        sums[idx] = sum;
    }
}

// Kernel to check for adjacent duplicates after sorting
__global__ void check_adjacent_duplicates_kernel(
    const uint64_t* sums,
    uint64_t total_subsets,
    int* d_collision_flag,
    uint64_t* d_collision_val
) {
    uint64_t idx = blockIdx.x * (uint64_t)blockDim.x + threadIdx.x;
    if (idx > 0 && idx < total_subsets) {
        if (sums[idx] == sums[idx - 1]) {
            *d_collision_flag = 1;
            *d_collision_val = sums[idx];
        }
    }
}

std::vector<uint64_t> parse_set_string(const std::string& input) {
    std::vector<uint64_t> result;
    std::string s = input;
    for (char& c : s) {
        if (c == '[' || c == ']' || c == '{' || c == '}' || c == ',' || c == ':') {
            c = ' ';
        }
    }
    std::stringstream ss(s);
    std::string token;
    while (ss >> token) {
        if (token == "\"set\"" || token == "set" || token == "\"n\"" || token == "n") {
            continue;
        }
        try {
            uint64_t val = std::stoull(token);
            result.push_back(val);
        } catch (...) {}
    }
    return result;
}

int main(int argc, char** argv) {
    std::string input_str;
    if (argc >= 3 && std::string(argv[1]) == "--set") {
        input_str = argv[2];
    } else {
        std::string line;
        while (std::getline(std::cin, line)) {
            input_str += " " + line;
        }
    }

    std::vector<uint64_t> elements = parse_set_string(input_str);
    if (elements.empty()) {
        std::cerr << "Error: No elements provided." << std::endl;
        return 2;
    }

    std::sort(elements.begin(), elements.end());
    int n = (int)elements.size();

    if (n > 30) {
        std::cerr << "Error: n=" << n << " exceeds GPU memory limit (max supported: 30)." << std::endl;
        return 2;
    }

    uint64_t max_val = elements.back();
    double ratio = (double)max_val / std::pow(2.0, (double)n);
    bool beats_bohman = (ratio < BOHMAN_CONSTANT);

    // Immediate check for duplicate elements in input
    for (int i = 1; i < n; ++i) {
        if (elements[i] == elements[i - 1]) {
            std::cout << "{\"valid\":false,\"n\":" << n
                      << ",\"max_val\":" << max_val
                      << ",\"ratio\":" << ratio
                      << ",\"beats_bohman\":" << (beats_bohman ? "true" : "false")
                      << ",\"collision\":[" << elements[i] << "," << elements[i] << "]"
                      << ",\"gpu_time_ms\":0.0}" << std::endl;
            return 1;
        }
    }

    uint64_t total_subsets = 1ULL << n;

    // Allocate Device Memory
    cudaEvent_t start, stop;
    cudaEventCreate(&start);
    cudaEventCreate(&stop);
    cudaEventRecord(start);

    // Copy elements to constant memory
    cudaMemcpyToSymbol(d_const_elements, elements.data(), sizeof(uint64_t) * n);

    uint64_t* d_sums = nullptr;
    cudaError_t err = cudaMalloc(&d_sums, sizeof(uint64_t) * total_subsets);
    if (err != cudaSuccess) {
        std::cerr << "CUDA Malloc Failed for " << total_subsets << " elements: "
                  << cudaGetErrorString(err) << std::endl;
        return 2;
    }

    int blockSize = 256;
    uint64_t numBlocks = (total_subsets + blockSize - 1) / blockSize;

    // Launch subset sums generation
    generate_subset_sums_kernel<<<numBlocks, blockSize>>>(d_sums, total_subsets, n);
    cudaDeviceSynchronize();

    // GPU Radix Sort via Thrust
    thrust::device_ptr<uint64_t> dev_ptr(d_sums);
    thrust::sort(dev_ptr, dev_ptr + total_subsets);

    // Check for collisions
    int* d_collision_flag;
    uint64_t* d_collision_val;
    cudaMalloc(&d_collision_flag, sizeof(int));
    cudaMalloc(&d_collision_val, sizeof(uint64_t));
    cudaMemset(d_collision_flag, 0, sizeof(int));

    check_adjacent_duplicates_kernel<<<numBlocks, blockSize>>>(d_sums, total_subsets, d_collision_flag, d_collision_val);
    cudaDeviceSynchronize();

    int h_collision_flag = 0;
    uint64_t h_collision_val = 0;
    cudaMemcpy(&h_collision_flag, d_collision_flag, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_collision_val, d_collision_val, sizeof(uint64_t), cudaMemcpyDeviceToHost);

    cudaEventRecord(stop);
    cudaEventSynchronize(stop);
    float milliseconds = 0.0f;
    cudaEventElapsedTime(&milliseconds, start, stop);

    // Cleanup
    cudaFree(d_sums);
    cudaFree(d_collision_flag);
    cudaFree(d_collision_val);
    cudaEventDestroy(start);
    cudaEventDestroy(stop);

    bool is_valid = (h_collision_flag == 0);

    std::cout << "{\"valid\":" << (is_valid ? "true" : "false")
              << ",\"n\":" << n
              << ",\"max_val\":" << max_val
              << ",\"ratio\":" << ratio
              << ",\"beats_bohman\":" << (beats_bohman ? "true" : "false")
              << ",\"collision\":";
    if (is_valid) {
        std::cout << "null";
    } else {
        std::cout << "[" << h_collision_val << "," << h_collision_val << "]";
    }
    std::cout << ",\"gpu_time_ms\":" << milliseconds << "}" << std::endl;

    return is_valid ? 0 : 1;
}
