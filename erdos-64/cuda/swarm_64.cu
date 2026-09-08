#include <iostream>
#include <vector>
#include <chrono>
#include <cstdint>
#include <curand_kernel.h>
#include <cuda_runtime.h>

#define MAX_V 64

// Fast bitwise 4-cycle count
__device__ int count_c4(const uint64_t* adj, int n) {
    int count = 0;
    for (int u = 0; u < n; ++u) {
        for (int w = u + 1; w < n; ++w) {
            int common = __popcll(adj[u] & adj[w]);
            if (common >= 2) {
                count += (common * (common - 1)) / 2;
            }
        }
    }
    return count;
}

// Fast bounded DFS for 8-cycles
__device__ int count_c8(const uint64_t* adj, int n) {
    int count = 0;
    for (int start = 0; start <= n - 8; ++start) {
        uint64_t mask_start = ~((1ULL << (start + 1)) - 1);
        uint64_t n1 = adj[start] & mask_start;
        while (n1) {
            int v1 = __ffsll(n1) - 1;
            n1 &= n1 - 1;
            uint64_t vis1 = (1ULL << start) | (1ULL << v1);

            uint64_t n2 = adj[v1] & mask_start & ~vis1;
            while (n2) {
                int v2 = __ffsll(n2) - 1;
                n2 &= n2 - 1;
                uint64_t vis2 = vis1 | (1ULL << v2);

                uint64_t n3 = adj[v2] & mask_start & ~vis2;
                while (n3) {
                    int v3 = __ffsll(n3) - 1;
                    n3 &= n3 - 1;
                    uint64_t vis3 = vis2 | (1ULL << v3);

                    uint64_t n4 = adj[v3] & mask_start & ~vis3;
                    while (n4) {
                        int v4 = __ffsll(n4) - 1;
                        n4 &= n4 - 1;
                        uint64_t vis4 = vis3 | (1ULL << v4);

                        uint64_t n5 = adj[v4] & mask_start & ~vis4;
                        while (n5) {
                            int v5 = __ffsll(n5) - 1;
                            n5 &= n5 - 1;
                            uint64_t vis5 = vis4 | (1ULL << v5);

                            uint64_t n6 = adj[v5] & mask_start & ~vis5;
                            while (n6) {
                                int v6 = __ffsll(n6) - 1;
                                n6 &= n6 - 1;
                                uint64_t vis6 = vis5 | (1ULL << v6);

                                uint64_t n7 = adj[v6] & mask_start & ~vis6;
                                while (n7) {
                                    int v7 = __ffsll(n7) - 1;
                                    n7 &= n7 - 1;
                                    if ((adj[v7] & (1ULL << start)) != 0) {
                                        count++;
                                        if (count > 20) return count; // Early bound
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return count;
}

// Swarm simulated annealing kernel
__global__ void swarm_search_kernel(
    int n,
    int iterations_per_thread,
    float initial_temp,
    float cooling_rate,
    int* d_found_flag,
    uint64_t* d_winning_adj,
    int* d_best_energy
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    curandState rng;
    curand_init(1234ULL + tid, 0, 0, &rng);

    // Initialize random 3-regular graph: ring of n vertices plus 1 random chord per vertex
    uint64_t adj[MAX_V];
    for (int i = 0; i < n; ++i) adj[i] = 0;

    // Ring edges: (i, (i+1)%n)
    for (int i = 0; i < n; ++i) {
        int next = (i + 1) % n;
        adj[i] |= (1ULL << next);
        adj[next] |= (1ULL << i);
    }
    // Random chord permutation for third degree
    int chords[MAX_V];
    for (int i = 0; i < n; ++i) chords[i] = i;
    for (int i = n - 1; i > 0; --i) {
        int j = curand(&rng) % (i + 1);
        int tmp = chords[i]; chords[i] = chords[j]; chords[j] = tmp;
    }
    for (int i = 0; i < n; i += 2) {
        int u = chords[i];
        int v = chords[i + 1];
        if (u != v && ((adj[u] & (1ULL << v)) == 0)) {
            adj[u] |= (1ULL << v);
            adj[v] |= (1ULL << u);
        }
    }

    // Energy = 50 * C4 + 10 * C8
    int c4 = count_c4(adj, n);
    int c8 = (c4 == 0) ? count_c8(adj, n) : 10;
    int energy = c4 * 50 + c8 * 10;

    float T = initial_temp;

    for (int step = 0; step < iterations_per_thread; ++step) {
        if (*d_found_flag) return;

        // Propose double-edge swap (2-opt)
        int u = curand(&rng) % n;
        uint64_t u_neighbors = adj[u];
        if (!u_neighbors) continue;
        int v_idx = curand(&rng) % __popcll(u_neighbors);
        int v = 0;
        uint64_t temp = u_neighbors;
        for (int k = 0; k <= v_idx; ++k) {
            v = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        int x = curand(&rng) % n;
        while (x == u || x == v) x = curand(&rng) % n;
        uint64_t x_neighbors = adj[x];
        if (!x_neighbors) continue;
        int y_idx = curand(&rng) % __popcll(x_neighbors);
        int y = 0;
        temp = x_neighbors;
        for (int k = 0; k <= y_idx; ++k) {
            y = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        if (y == u || y == v || x == y) continue;
        // Check if new edges (u, x) and (v, y) don't already exist
        if ((adj[u] & (1ULL << x)) || (adj[v] & (1ULL << y))) continue;

        // Apply tentative swap
        adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
        adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
        adj[u] |= (1ULL << x); adj[x] |= (1ULL << u);
        adj[v] |= (1ULL << y); adj[y] |= (1ULL << v);

        int new_c4 = count_c4(adj, n);
        int new_c8 = (new_c4 == 0) ? count_c8(adj, n) : 10;
        int new_energy = new_c4 * 50 + new_c8 * 10;

        int delta = new_energy - energy;
        bool accept = false;
        if (delta <= 0) {
            accept = true;
        } else {
            float prob = expf(-((float)delta) / T);
            if (curand_uniform(&rng) < prob) {
                accept = true;
            }
        }

        if (accept) {
            energy = new_energy;
            c4 = new_c4;
            c8 = new_c8;
            if (energy == 0) {
                // Found graph with NO C4 and NO C8!
                atomicExch(d_found_flag, 1);
                for (int i = 0; i < n; ++i) {
                    d_winning_adj[i] = adj[i];
                }
                atomicMin(d_best_energy, 0);
                return;
            }
        } else {
            // Revert swap
            adj[u] &= ~(1ULL << x); adj[x] &= ~(1ULL << u);
            adj[v] &= ~(1ULL << y); adj[y] &= ~(1ULL << v);
            adj[u] |= (1ULL << v); adj[v] |= (1ULL << u);
            adj[x] |= (1ULL << y); adj[y] |= (1ULL << x);
        }

        T *= cooling_rate;
    }

    atomicMin(d_best_energy, energy);
}

int main(int argc, char** argv) {
    int n = 32;
    int total_threads = 10240;
    int iterations = 1000;
    if (argc >= 2) n = std::atoi(argv[1]);
    if (argc >= 3) iterations = std::atoi(argv[2]);

    std::cout << "=== Erdős #64 GPU Swarm Searcher (RTX 4070 Super) ===" << std::endl;
    std::cout << "Vertices n: " << n << " | Threads: " << total_threads
              << " | Iterations/Thread: " << iterations << std::endl;

    int* d_found_flag;
    int* d_best_energy;
    uint64_t* d_winning_adj;
    cudaMalloc(&d_found_flag, sizeof(int));
    cudaMalloc(&d_best_energy, sizeof(int));
    cudaMalloc(&d_winning_adj, sizeof(uint64_t) * n);

    cudaMemset(d_found_flag, 0, sizeof(int));
    int initial_energy = 999999;
    cudaMemcpy(d_best_energy, &initial_energy, sizeof(int), cudaMemcpyHostToDevice);

    int blockSize = 256;
    int numBlocks = (total_threads + blockSize - 1) / blockSize;

    auto start_time = std::chrono::high_resolution_clock::now();

    swarm_search_kernel<<<numBlocks, blockSize>>>(
        n, iterations, 5.0f, 0.999f, d_found_flag, d_winning_adj, d_best_energy
    );
    cudaDeviceSynchronize();

    auto end_time = std::chrono::high_resolution_clock::now();
    double duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

    int h_found = 0;
    int h_best_energy = 0;
    cudaMemcpy(&h_found, d_found_flag, sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(&h_best_energy, d_best_energy, sizeof(int), cudaMemcpyDeviceToHost);

    std::cout << "Swarm completed in " << duration_ms << " ms ("
              << (total_threads * (uint64_t)iterations / (duration_ms / 1000.0) / 1e6)
              << " million moves/sec)!" << std::endl;
    std::cout << "Best Energy reached in swarm: " << h_best_energy << std::endl;

    if (h_found) {
        std::vector<uint64_t> winning(n);
        cudaMemcpy(winning.data(), d_winning_adj, sizeof(uint64_t) * n, cudaMemcpyDeviceToHost);
        std::cout << "🎉 NOVEL CANDIDATE WITH ZERO C4/C8 FOUND! Exporting adjacency:" << std::endl;
        std::cout << "{\"n\":" << n << ",\"adj\":[";
        for (int i = 0; i < n; ++i) {
            std::cout << "[";
            bool first = true;
            for (int j = 0; j < n; ++j) {
                if (winning[i] & (1ULL << j)) {
                    if (!first) std::cout << ",";
                    std::cout << j;
                    first = false;
                }
            }
            std::cout << "]" << (i + 1 < n ? "," : "");
        }
        std::cout << "]}" << std::endl;
    } else {
        std::cout << "No counterexample discovered in this batch. Keep searching or increase iterations." << std::endl;
    }

    cudaFree(d_found_flag);
    cudaFree(d_best_energy);
    cudaFree(d_winning_adj);

    return 0;
}
