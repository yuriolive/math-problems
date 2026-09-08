#include <iostream>
#include <fstream>
#include <sstream>
#include <vector>
#include <string>
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

// Swarm simulated annealing kernel supporting seed graphs, diverse temperatures, and ILS
__global__ void swarm_search_kernel(
    int n,
    int iterations_per_thread,
    float initial_temp,
    float cooling_rate,
    int* d_found_flag,
    uint64_t* d_winning_adj,
    int* d_all_best_energy,
    uint64_t* d_all_best_adj,
    const uint64_t* d_seed_adj,
    int has_seed
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    curandState rng;
    curand_init(1234ULL + tid, 0, 0, &rng);

    uint64_t adj[MAX_V];
    for (int i = 0; i < n; ++i) adj[i] = 0;

    if (has_seed) {
        // Initialize from seed graph
        for (int i = 0; i < n; ++i) {
            adj[i] = d_seed_adj[i];
        }
        // Thread 0 keeps exact seed; other threads perturb with small 2-opt warmup
        int perturb = tid % 16;
        for (int p = 0; p < perturb; ++p) {
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
            int mode = curand(&rng) % 2;
            int n1_a = u, n1_b = (mode == 0) ? x : y;
            int n2_a = v, n2_b = (mode == 0) ? y : x;
            if ((adj[n1_a] & (1ULL << n1_b)) || (adj[n2_a] & (1ULL << n2_b))) continue;

            adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
            adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
            adj[n1_a] |= (1ULL << n1_b); adj[n1_b] |= (1ULL << n1_a);
            adj[n2_a] |= (1ULL << n2_b); adj[n2_b] |= (1ULL << n2_a);
        }
    } else {
        // Initialize from Möbius ladder + 100 random 2-opt scramble moves
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

            adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
            adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
            adj[u] |= (1ULL << x); adj[x] |= (1ULL << u);
            adj[v] |= (1ULL << y); adj[y] |= (1ULL << v);
        }
    }

    int c4, c8, c16, c32;
    int energy = compute_energy(adj, n, c4, c8, c16, c32);

    int local_best_energy = energy;
    uint64_t local_best_adj[MAX_V];
    for (int i = 0; i < n; ++i) local_best_adj[i] = adj[i];
    int steps_since_improvement = 0;

    // Diverse temperatures across threads (RTX 4070 Super parallel tempering spectrum):
    // Some threads cold/greedy (T=0.4), some medium (T=4.0), some hot (T=20.0)
    float temp_mult = 0.05f + 2.5f * ((float)(tid % 128) / 127.0f);
    float thread_initial_temp = initial_temp * temp_mult;
    float T = thread_initial_temp;

    for (int step = 0; step < iterations_per_thread; ++step) {
        if (*d_found_flag) {
            d_all_best_energy[tid] = local_best_energy;
            for (int i = 0; i < n; ++i) d_all_best_adj[tid * n + i] = local_best_adj[i];
            return;
        }

        bool is_3opt = (curand_uniform(&rng) < 0.25f);
        int move_type = 2;

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

        int n1_a = 0, n1_b = 0, n2_a = 0, n2_b = 0;
        int w = 0, z = 0, n3_a = 0, n3_b = 0;

        if (is_3opt) {
            w = curand(&rng) % n;
            if (w == u || w == v || w == x || w == y) continue;
            uint64_t w_nbrs = adj[w];
            int z_idx = curand(&rng) % 3;
            temp = w_nbrs;
            for (int k = 0; k <= z_idx; ++k) {
                z = __ffsll(temp) - 1;
                temp &= temp - 1;
            }
            if (z == u || z == v || z == x || z == y || z == w) continue;

            int mode = curand(&rng) % 2;
            if (mode == 0) {
                n1_a = u; n1_b = x;
                n2_a = y; n2_b = w;
                n3_a = z; n3_b = v;
            } else {
                n1_a = u; n1_b = y;
                n2_a = x; n2_b = z;
                n3_a = w; n3_b = v;
            }

            if ((adj[n1_a] & (1ULL << n1_b)) || (adj[n2_a] & (1ULL << n2_b)) || (adj[n3_a] & (1ULL << n3_b))) continue;

            adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
            adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
            adj[w] &= ~(1ULL << z); adj[z] &= ~(1ULL << w);

            adj[n1_a] |= (1ULL << n1_b); adj[n1_b] |= (1ULL << n1_a);
            adj[n2_a] |= (1ULL << n2_b); adj[n2_b] |= (1ULL << n2_a);
            adj[n3_a] |= (1ULL << n3_b); adj[n3_b] |= (1ULL << n3_a);
            move_type = 3;
        } else {
            int mode = curand(&rng) % 2;
            n1_a = u; n1_b = (mode == 0) ? x : y;
            n2_a = v; n2_b = (mode == 0) ? y : x;

            if ((adj[n1_a] & (1ULL << n1_b)) || (adj[n2_a] & (1ULL << n2_b))) continue;

            adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
            adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
            adj[n1_a] |= (1ULL << n1_b); adj[n1_b] |= (1ULL << n1_a);
            adj[n2_a] |= (1ULL << n2_b); adj[n2_b] |= (1ULL << n2_a);
            move_type = 2;
        }

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

            if (energy < local_best_energy) {
                local_best_energy = energy;
                for (int i = 0; i < n; ++i) local_best_adj[i] = adj[i];
                steps_since_improvement = 0;
            } else {
                steps_since_improvement++;
            }

            if (energy == 0) {
                atomicExch(d_found_flag, 1);
                for (int i = 0; i < n; ++i) {
                    d_winning_adj[i] = adj[i];
                    d_all_best_adj[tid * n + i] = adj[i];
                }
                d_all_best_energy[tid] = 0;
                return;
            }
        } else {
            if (move_type == 3) {
                adj[n1_a] &= ~(1ULL << n1_b); adj[n1_b] &= ~(1ULL << n1_a);
                adj[n2_a] &= ~(1ULL << n2_b); adj[n2_b] &= ~(1ULL << n2_a);
                adj[n3_a] &= ~(1ULL << n3_b); adj[n3_b] &= ~(1ULL << n3_a);
                adj[u] |= (1ULL << v); adj[v] |= (1ULL << u);
                adj[x] |= (1ULL << y); adj[y] |= (1ULL << x);
                adj[w] |= (1ULL << z); adj[z] |= (1ULL << w);
            } else {
                adj[n1_a] &= ~(1ULL << n1_b); adj[n1_b] &= ~(1ULL << n1_a);
                adj[n2_a] &= ~(1ULL << n2_b); adj[n2_b] &= ~(1ULL << n2_a);
                adj[u] |= (1ULL << v); adj[v] |= (1ULL << u);
                adj[x] |= (1ULL << y); adj[y] |= (1ULL << x);
            }
            steps_since_improvement++;
        }

        T *= cooling_rate;

        // Iterated Local Search (ILS): if stagnated for 2000 steps, snap back to best and reheat
        if (steps_since_improvement >= 2000) {
            for (int i = 0; i < n; ++i) adj[i] = local_best_adj[i];
            energy = local_best_energy;
            T = thread_initial_temp * 0.7f;
            steps_since_improvement = 0;
        }
    }

    d_all_best_energy[tid] = local_best_energy;
    for (int i = 0; i < n; ++i) {
        d_all_best_adj[tid * n + i] = local_best_adj[i];
    }
}

// Fast JSON parser for adjacency lists
bool parse_seed_json(const std::string& json_str, int& n, std::vector<uint64_t>& adj_out) {
    size_t n_pos = json_str.find("\"n\"");
    if (n_pos != std::string::npos) {
        size_t colon = json_str.find(":", n_pos);
        if (colon != std::string::npos) {
            int parsed_n = 0;
            size_t k = colon + 1;
            while (k < json_str.size() && !isdigit(json_str[k])) k++;
            while (k < json_str.size() && isdigit(json_str[k])) {
                parsed_n = parsed_n * 10 + (json_str[k] - '0');
                k++;
            }
            if (parsed_n > 0) n = parsed_n;
        }
    }

    adj_out.assign(n, 0);
    size_t adj_pos = json_str.find("\"adj\"");
    if (adj_pos == std::string::npos) return false;
    size_t start = json_str.find("[", adj_pos);
    if (start == std::string::npos) return false;

    int u = 0;
    size_t i = start + 1;
    while (i < json_str.size() && u < n) {
        while (i < json_str.size() && json_str[i] != '[' && json_str[i] != ']') {
            i++;
        }
        if (i >= json_str.size() || json_str[i] == ']') break;
        i++; // skip '['

        while (i < json_str.size() && json_str[i] != ']') {
            while (i < json_str.size() && !isdigit(json_str[i]) && json_str[i] != ']') i++;
            if (json_str[i] == ']') break;
            int v = 0;
            while (i < json_str.size() && isdigit(json_str[i])) {
                v = v * 10 + (json_str[i] - '0');
                i++;
            }
            if (u < n && v < n && u != v) {
                adj_out[u] |= (1ULL << v);
                adj_out[v] |= (1ULL << u);
            }
        }
        u++;
        if (i < json_str.size() && json_str[i] == ']') i++;
    }
    return (u == n);
}

int main(int argc, char** argv) {
    int n = 32;
    int total_threads = 10240;
    int iterations = 2000;
    bool json_only = false;
    std::string seed_json_str = "";

    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--json-only") {
            json_only = true;
        } else if (arg == "--seed-json" && i + 1 < argc) {
            seed_json_str = argv[++i];
        } else if (arg == "--seed-file" && i + 1 < argc) {
            std::ifstream f(argv[++i]);
            if (f.is_open()) {
                std::stringstream ss;
                ss << f.rdbuf();
                seed_json_str = ss.str();
            }
        } else if (isdigit(arg[0])) {
            if (i == 1) n = std::atoi(arg.c_str());
            else if (i == 2) iterations = std::atoi(arg.c_str());
        }
    }

    std::vector<uint64_t> seed_adj;
    int has_seed = 0;
    if (!seed_json_str.empty()) {
        if (parse_seed_json(seed_json_str, n, seed_adj)) {
            has_seed = 1;
        }
    }

    if (n % 2 != 0) {
        std::cerr << "Error: 3-regular graphs must have an even number of vertices!" << std::endl;
        return 1;
    }

    if (!json_only) {
        std::cout << "=== Erdős #64 GPU Swarm Searcher (RTX 4070 Super) ===" << std::endl;
        std::cout << "Vertices n: " << n << " | Threads: " << total_threads
                  << " | Iterations/Thread: " << iterations << std::endl;
        std::cout << "Mode: " << (has_seed ? "Seeded Annealing (Micro-Polishing)" : "Full Stochastic Search") << std::endl;
    }

    int* d_found_flag;
    int* d_all_best_energy;
    uint64_t* d_winning_adj;
    uint64_t* d_all_best_adj;
    uint64_t* d_seed_adj = nullptr;

    cudaMalloc(&d_found_flag, sizeof(int));
    cudaMalloc(&d_all_best_energy, sizeof(int) * total_threads);
    cudaMalloc(&d_winning_adj, sizeof(uint64_t) * n);
    cudaMalloc(&d_all_best_adj, sizeof(uint64_t) * n * total_threads);

    if (has_seed) {
        cudaMalloc(&d_seed_adj, sizeof(uint64_t) * n);
        cudaMemcpy(d_seed_adj, seed_adj.data(), sizeof(uint64_t) * n, cudaMemcpyHostToDevice);
    }

    cudaMemset(d_found_flag, 0, sizeof(int));

    int blockSize = 256;
    int numBlocks = (total_threads + blockSize - 1) / blockSize;

    auto start_time = std::chrono::high_resolution_clock::now();

    swarm_search_kernel<<<numBlocks, blockSize>>>(
        n, iterations, 8.0f, 0.9997f, d_found_flag, d_winning_adj, d_all_best_energy, d_all_best_adj, d_seed_adj, has_seed
    );
    cudaDeviceSynchronize();

    auto end_time = std::chrono::high_resolution_clock::now();
    double duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

    int h_found = 0;
    cudaMemcpy(&h_found, d_found_flag, sizeof(int), cudaMemcpyDeviceToHost);

    std::vector<int> h_energies(total_threads);
    cudaMemcpy(h_energies.data(), d_all_best_energy, sizeof(int) * total_threads, cudaMemcpyDeviceToHost);

    int best_tid = 0;
    int h_best_energy = h_energies[0];
    for (int t = 1; t < total_threads; ++t) {
        if (h_energies[t] < h_best_energy) {
            h_best_energy = h_energies[t];
            best_tid = t;
        }
    }

    std::vector<uint64_t> final_adj(n);
    if (h_found) {
        cudaMemcpy(final_adj.data(), d_winning_adj, sizeof(uint64_t) * n, cudaMemcpyDeviceToHost);
        h_best_energy = 0;
    } else {
        cudaMemcpy(final_adj.data(), d_all_best_adj + best_tid * n, sizeof(uint64_t) * n, cudaMemcpyDeviceToHost);
    }

    if (json_only) {
        std::cout << "{\"counterexample\":" << (h_found ? "true" : "false")
                  << ",\"best_energy\":" << h_best_energy
                  << ",\"n\":" << n
                  << ",\"adj\":[";
        for (int i = 0; i < n; ++i) {
            std::cout << "[";
            bool first = true;
            for (int j = 0; j < n; ++j) {
                if (final_adj[i] & (1ULL << j)) {
                    if (!first) std::cout << ",";
                    std::cout << j;
                    first = false;
                }
            }
            std::cout << "]" << (i + 1 < n ? "," : "");
        }
        std::cout << "]}" << std::endl;
    } else {
        std::cout << "Swarm completed in " << duration_ms << " ms ("
                  << (total_threads * (uint64_t)iterations / (duration_ms / 1000.0) / 1e6)
                  << " million moves/sec)!" << std::endl;
        std::cout << "Best Energy reached in swarm: " << h_best_energy << std::endl;

        if (h_found) {
            std::cout << "🎉🎉🎉 UNPRECEDENTED COUNTEREXAMPLE WITH ZERO 2^k CYCLES DISCOVERED! 🎉🎉🎉" << std::endl;
        }
        std::cout << "{\"n\":" << n << ",\"adj\":[";
        for (int i = 0; i < n; ++i) {
            std::cout << "[";
            bool first = true;
            for (int j = 0; j < n; ++j) {
                if (final_adj[i] & (1ULL << j)) {
                    if (!first) std::cout << ",";
                    std::cout << j;
                    first = false;
                }
            }
            std::cout << "]" << (i + 1 < n ? "," : "");
        }
        std::cout << "]}" << std::endl;
    }

    cudaFree(d_found_flag);
    cudaFree(d_all_best_energy);
    cudaFree(d_winning_adj);
    cudaFree(d_all_best_adj);
    if (d_seed_adj) cudaFree(d_seed_adj);

    return (h_found ? 0 : 1);
}
