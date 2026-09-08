#include <iostream>
#include <vector>
#include <chrono>
#include <cstdint>
#include <cmath>
#include <curand_kernel.h>
#include <cuda_runtime.h>

#define MAX_V 64

// Fast bitwise 4-cycle count (counts each C4 twice: once per opposite vertex pair)
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
    if (n < 8) return 0;
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
                                        if (count >= 10) return count;
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

// Bounded iterative DFS for 16-cycles
__device__ int count_c16(const uint64_t* adj, int n) {
    if (n < 16) return 0;
    int count = 0;
    for (int start = 0; start <= n - 16; ++start) {
        uint64_t mask_start = ~((1ULL << (start + 1)) - 1);
        int stack_v[16];
        uint64_t stack_cands[16];
        uint64_t visited = 1ULL << start;

        stack_v[0] = start;
        stack_cands[0] = adj[start] & mask_start;
        int depth = 0;

        while (depth >= 0) {
            if (stack_cands[depth] != 0) {
                int nxt = __ffsll(stack_cands[depth]) - 1;
                stack_cands[depth] &= stack_cands[depth] - 1;

                if (depth == 14) {
                    if ((adj[nxt] & (1ULL << start)) != 0) {
                        count++;
                        if (count >= 5) return count;
                    }
                } else {
                    depth++;
                    stack_v[depth] = nxt;
                    visited |= (1ULL << nxt);
                    stack_cands[depth] = adj[nxt] & mask_start & ~visited;
                }
            } else {
                if (depth > 0) {
                    visited &= ~(1ULL << stack_v[depth]);
                }
                depth--;
            }
        }
    }
    return count;
}

// Bounded iterative DFS for 32-cycles
__device__ int count_c32(const uint64_t* adj, int n) {
    if (n < 32) return 0;
    int count = 0;
    for (int start = 0; start <= n - 32; ++start) {
        uint64_t mask_start = ~((1ULL << (start + 1)) - 1);
        int stack_v[32];
        uint64_t stack_cands[32];
        uint64_t visited = 1ULL << start;

        stack_v[0] = start;
        stack_cands[0] = adj[start] & mask_start;
        int depth = 0;

        while (depth >= 0) {
            if (stack_cands[depth] != 0) {
                int nxt = __ffsll(stack_cands[depth]) - 1;
                stack_cands[depth] &= stack_cands[depth] - 1;

                if (depth == 30) {
                    if ((adj[nxt] & (1ULL << start)) != 0) {
                        count++;
                        if (count >= 5) return count;
                    }
                } else {
                    depth++;
                    stack_v[depth] = nxt;
                    visited |= (1ULL << nxt);
                    stack_cands[depth] = adj[nxt] & mask_start & ~visited;
                }
            } else {
                if (depth > 0) {
                    visited &= ~(1ULL << stack_v[depth]);
                }
                depth--;
            }
        }
    }
    return count;
}

// Multi-tier energy evaluation: computes higher cycle penalties only when lower cycles are zero
__device__ int compute_energy(const uint64_t* adj, int n, int& c4, int& c8, int& c16, int& c32) {
    c4 = count_c4(adj, n);
    if (c4 > 0) {
        c8 = 5;
        c16 = 5;
        c32 = (n >= 32) ? 5 : 0;
        return c4 * 1000 + 500;
    }
    c8 = count_c8(adj, n);
    if (c8 > 0) {
        c16 = 5;
        c32 = (n >= 32) ? 5 : 0;
        return c8 * 200 + 100;
    }
    c16 = count_c16(adj, n);
    if (c16 > 0) {
        c32 = (n >= 32) ? 5 : 0;
        return c16 * 50 + 20;
    }
    if (n >= 32) {
        c32 = count_c32(adj, n);
        return c32 * 10;
    }
    c32 = 0;
    return 0; // True counterexample: C4=0, C8=0, C16=0, C32=0!
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

    // 1. Initialize guaranteed 3-regular graph:
    // Outer ring C_n: (i, (i+1)%n) and (i, (i-1+n)%n)
    // + Möbius ladder chords: (i, (i + n/2)%n)
    // Since n is even and n >= 8, all 3 edges per vertex are strictly distinct.
    uint64_t adj[MAX_V];
    for (int i = 0; i < n; ++i) adj[i] = 0;

    for (int i = 0; i < n; ++i) {
        int nxt = (i + 1) % n;
        adj[i] |= (1ULL << nxt);
        adj[nxt] |= (1ULL << i);
    }
    int half = n / 2;
    for (int i = 0; i < half; ++i) {
        int j = i + half;
        adj[i] |= (1ULL << j);
        adj[j] |= (1ULL << i);
    }

    // Warmup scramble: perform 100 random valid 2-opt swaps to randomize topology
    for (int w = 0; w < 100; ++w) {
        int u = curand(&rng) % n;
        uint64_t u_nbrs = adj[u];
        int v_idx = curand(&rng) % 3;
        int v = 0;
        uint64_t temp = u_nbrs;
        for (int k = 0; k <= v_idx; ++k) {
            v = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        int x = curand(&rng) % n;
        if (x == u || x == v) continue;
        uint64_t x_nbrs = adj[x];
        int y_idx = curand(&rng) % 3;
        int y = 0;
        temp = x_nbrs;
        for (int k = 0; k <= y_idx; ++k) {
            y = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        if (y == u || y == v || x == y) continue;
        if ((adj[u] & (1ULL << x)) || (adj[v] & (1ULL << y))) continue;

        // Apply swap
        adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
        adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
        adj[u] |= (1ULL << x); adj[x] |= (1ULL << u);
        adj[v] |= (1ULL << y); adj[y] |= (1ULL << v);
    }

    int c4, c8, c16, c32;
    int energy = compute_energy(adj, n, c4, c8, c16, c32);

    float T = initial_temp;

    for (int step = 0; step < iterations_per_thread; ++step) {
        if (*d_found_flag) return;

        // Propose 2-opt edge swap
        int u = curand(&rng) % n;
        uint64_t u_nbrs = adj[u];
        int v_idx = curand(&rng) % 3;
        int v = 0;
        uint64_t temp = u_nbrs;
        for (int k = 0; k <= v_idx; ++k) {
            v = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        int x = curand(&rng) % n;
        if (x == u || x == v) continue;
        uint64_t x_nbrs = adj[x];
        int y_idx = curand(&rng) % 3;
        int y = 0;
        temp = x_nbrs;
        for (int k = 0; k <= y_idx; ++k) {
            y = __ffsll(temp) - 1;
            temp &= temp - 1;
        }

        if (y == u || y == v || x == y) continue;

        // Randomly pick pairing A (u-x, v-y) or pairing B (u-y, v-x)
        int mode = curand(&rng) % 2;
        int n1_a = u, n1_b = (mode == 0) ? x : y;
        int n2_a = v, n2_b = (mode == 0) ? y : x;

        // Check if new edges already exist
        if ((adj[n1_a] & (1ULL << n1_b)) || (adj[n2_a] & (1ULL << n2_b))) continue;

        // Apply tentative swap
        adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
        adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
        adj[n1_a] |= (1ULL << n1_b); adj[n1_b] |= (1ULL << n1_a);
        adj[n2_a] |= (1ULL << n2_b); adj[n2_b] |= (1ULL << n2_a);

        int new_c4, new_c8, new_c16, new_c32;
        int new_energy = compute_energy(adj, n, new_c4, new_c8, new_c16, new_c32);

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
            c16 = new_c16;
            c32 = new_c32;

            if (energy == 0) {
                // GENUINE COUNTEREXAMPLE: ZERO 2^k CYCLES (C4=0, C8=0, C16=0, C32=0)!
                atomicExch(d_found_flag, 1);
                for (int i = 0; i < n; ++i) {
                    d_winning_adj[i] = adj[i];
                }
                atomicMin(d_best_energy, 0);
                return;
            }
        } else {
            // Revert swap
            adj[n1_a] &= ~(1ULL << n1_b); adj[n1_b] &= ~(1ULL << n1_a);
            adj[n2_a] &= ~(1ULL << n2_b); adj[n2_b] &= ~(1ULL << n2_a);
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
    int iterations = 2000;
    if (argc >= 2) n = std::atoi(argv[1]);
    if (argc >= 3) iterations = std::atoi(argv[2]);

    if (n % 2 != 0) {
        std::cerr << "Error: 3-regular graphs must have even number of vertices!" << std::endl;
        return 1;
    }

    std::cout << "=== Erdős #64 Advanced GPU Swarm Searcher (RTX 4070 Super) ===" << std::endl;
    std::cout << "Vertices n: " << n << " | Threads: " << total_threads
              << " | Iterations/Thread: " << iterations << std::endl;
    std::cout << "Multi-Tier Target: Eliminating C4, C8, C16" << (n >= 32 ? ", and C32" : "") << std::endl;

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
        n, iterations, 8.0f, 0.9995f, d_found_flag, d_winning_adj, d_best_energy
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
        std::cout << "🎉🎉🎉 UNPRECEDENTED COUNTEREXAMPLE WITH ZERO 2^k CYCLES DISCOVERED! 🎉🎉🎉" << std::endl;
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
