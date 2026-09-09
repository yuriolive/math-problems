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
#define MAX_N_SUPPORTED 62

// Exact 4-cycle count, normalized to UNDIRECTED cycles so the numbers agree with
// verifier_64. Each C4 is seen once per opposite vertex pair, i.e. twice.
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
    return count / 2;
}

// Fast bounded DFS for 8-cycles
__device__ int count_c8(const uint64_t* adj, int n, int count_cap) {
    // Returns UNDIRECTED cycle count: each cycle is walked in both directions.
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
                                        if (count >= count_cap) return count / 2;
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    return count / 2;
}

// Bounded iterative DFS for 16-cycles
__device__ int count_c16(const uint64_t* adj, int n, int count_cap) {
    // Returns UNDIRECTED cycle count: each cycle is walked in both directions.
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
                        if (count >= count_cap) return count / 2;
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
    return count / 2;
}

// Bounded iterative DFS for 32-cycles
__device__ int count_c32(const uint64_t* adj, int n, int count_cap) {
    // Returns UNDIRECTED cycle count: each cycle is walked in both directions.
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
                        if (count >= count_cap) return count / 2;
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
    return count / 2;
}

// Multi-tier energy on TRUE cycle counts.
//
// Tiers are evaluated shallowest-first and a deeper tier is only reached once every
// shallower tier is empty; that conditional evaluation is what keeps the kernel fast.
// Counts are exact up to count_cap. Tiers that were never reached report -1
// ("not evaluated") rather than a fake value, so no caller can mistake an unevaluated
// tier for an empty one.
//
// C64: this kernel refuses n > 62, so 64 is never a possible cycle length here. The
// Rust verifier is the ground truth and does check C64 at n = 64.
//
// The energy is LEXICOGRAPHIC, not a weighted sum.
//
//   level  = how many of the shallow tiers are already empty
//            (0: C4 remains, 1: C4 clean, 2: C4+C8 clean, 3: C4+C8+C16 clean, 4: solved)
//   energy = (4 - level) * TIER_STRIDE + min(count at that level, TIER_STRIDE - 1)
//
// A weighted sum like 1000*c4 + 200*c8 + 50*c16 does the wrong thing once the counts
// are uncapped: a graph with one C8 (300) scores better than a graph with no C8 but
// 424 C16 (21220), so the search happily trades a shallow violation for a deep one.
// The lexicographic key makes any regression to a shallower tier cost TIER_STRIDE,
// while still giving a unit gradient inside the tier currently being worked on.
#define TIER_STRIDE 1000000

__device__ int compute_energy(const uint64_t* adj, int n, int count_cap,
                              int& c4, int& c8, int& c16, int& c32) {
    c8 = -1;
    c16 = -1;
    c32 = -1;

    // count_cap is an undirected budget; the DFS counters cap directed hits.
    int cap = count_cap < TIER_STRIDE ? 2 * count_cap : TIER_STRIDE - 1;

    c4 = count_c4(adj, n);
    if (c4 > 0) return 4 * TIER_STRIDE + (c4 < cap ? c4 : cap);

    c8 = count_c8(adj, n, cap);
    if (c8 > 0) return 3 * TIER_STRIDE + c8;

    c16 = count_c16(adj, n, cap);
    if (c16 > 0) return 2 * TIER_STRIDE + c16;

    if (n >= 32) {
        c32 = count_c32(adj, n, cap);
        if (c32 > 0) return 1 * TIER_STRIDE + c32;
    } else {
        c32 = 0;
    }
    return 0; // C4 = C8 = C16 = C32 = 0 -> candidate counterexample.
}

// One structure-preserving 2-opt swap, used for warmup and seed perturbation.
// Returns true when a swap was actually applied.
__device__ bool try_random_2opt(uint64_t* adj, int n, curandState* rng) {
    int u = curand(rng) % n;
    uint64_t temp = adj[u];
    int v_idx = curand(rng) % 3;
    int v = 0;
    for (int k = 0; k <= v_idx; ++k) { v = __ffsll(temp) - 1; temp &= temp - 1; }

    int x = curand(rng) % n;
    if (x == u || x == v) return false;
    temp = adj[x];
    int y_idx = curand(rng) % 3;
    int y = 0;
    for (int k = 0; k <= y_idx; ++k) { y = __ffsll(temp) - 1; temp &= temp - 1; }
    if (y == u || y == v || x == y) return false;

    int mode = curand(rng) % 2;
    int a1 = u, b1 = (mode == 0) ? x : y;
    int a2 = v, b2 = (mode == 0) ? y : x;
    if ((adj[a1] & (1ULL << b1)) || (adj[a2] & (1ULL << b2))) return false;

    adj[u] &= ~(1ULL << v); adj[v] &= ~(1ULL << u);
    adj[x] &= ~(1ULL << y); adj[y] &= ~(1ULL << x);
    adj[a1] |= (1ULL << b1); adj[b1] |= (1ULL << a1);
    adj[a2] |= (1ULL << b2); adj[b2] |= (1ULL << a2);
    return true;
}

// Swarm simulated annealing kernel supporting seed graphs, diverse temperatures, and ILS
__global__ void swarm_search_kernel(
    int n,
    int iterations_per_thread,
    float initial_temp,
    float cooling_rate,
    int count_cap,
    int stagnation_limit,
    int* d_found_flag,
    uint64_t* d_winning_adj,
    int* d_all_best_energy,
    uint64_t* d_all_best_adj,
    unsigned long long* d_moves_evaluated,
    const uint64_t* d_seed_adj,
    int has_seed
) {
    int tid = blockIdx.x * blockDim.x + threadIdx.x;
    curandState rng;
    curand_init(1234ULL + tid, 0, 0, &rng);

    uint64_t adj[MAX_V];
    for (int i = 0; i < n; ++i) adj[i] = 0;

    if (has_seed) {
        for (int i = 0; i < n; ++i) adj[i] = d_seed_adj[i];
        // Thread 0 keeps the exact seed; the others explore its 2-opt neighborhood.
        int perturb = tid % 16;
        for (int p = 0; p < perturb; ++p) try_random_2opt(adj, n, &rng);
    } else {
        // Moebius ladder C_n(1, n/2): cubic by construction, then scrambled.
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
        for (int w = 0; w < 100; ++w) try_random_2opt(adj, n, &rng);
    }

    int c4, c8, c16, c32;
    int energy = compute_energy(adj, n, count_cap, c4, c8, c16, c32);
    unsigned long long moves_evaluated = 1;

    int local_best_energy = energy;
    uint64_t local_best_adj[MAX_V];
    for (int i = 0; i < n; ++i) local_best_adj[i] = adj[i];
    int last_improve_step = 0;

    // Temperature spectrum across threads. Energy deltas are on the scale of the tier
    // key: inside a tier a single cycle is worth 1, so the useful temperature band is
    // small. Regressing a whole tier costs TIER_STRIDE and is effectively never taken.
    float temp_mult = 0.02f + 2.98f * ((float)(tid % 128) / 127.0f);
    float thread_initial_temp = initial_temp * temp_mult;
    float T = thread_initial_temp;

    for (int step = 0; step < iterations_per_thread; ++step) {
        if (*d_found_flag) break;

        // Cooling and the stagnation check run at the top of the loop so that they
        // still apply on iterations where move generation bails out early. The old
        // code put them at the bottom, after several `continue` statements.
        T *= cooling_rate;
        if (T < 0.05f) T = 0.05f;

        if (step - last_improve_step >= stagnation_limit) {
            for (int i = 0; i < n; ++i) adj[i] = local_best_adj[i];
            energy = local_best_energy;
            T = thread_initial_temp * 0.7f;
            last_improve_step = step;
        }

        bool is_3opt = (curand_uniform(&rng) < 0.25f);
        int move_type = 2;

        int u = curand(&rng) % n;
        int v_idx = curand(&rng) % 3;
        int v = 0;
        uint64_t temp = adj[u];
        for (int k = 0; k <= v_idx; ++k) { v = __ffsll(temp) - 1; temp &= temp - 1; }

        int x = curand(&rng) % n;
        if (x == u || x == v) continue;
        int y_idx = curand(&rng) % 3;
        int y = 0;
        temp = adj[x];
        for (int k = 0; k <= y_idx; ++k) { y = __ffsll(temp) - 1; temp &= temp - 1; }
        if (y == u || y == v || x == y) continue;

        int n1_a = 0, n1_b = 0, n2_a = 0, n2_b = 0;
        int w = 0, z = 0, n3_a = 0, n3_b = 0;

        if (is_3opt) {
            w = curand(&rng) % n;
            if (w == u || w == v || w == x || w == y) continue;
            int z_idx = curand(&rng) % 3;
            temp = adj[w];
            for (int k = 0; k <= z_idx; ++k) { z = __ffsll(temp) - 1; temp &= temp - 1; }
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
        int new_energy = compute_energy(adj, n, count_cap, new_c4, new_c8, new_c16, new_c32);
        moves_evaluated++;

        int delta = new_energy - energy;
        bool accept = (delta <= 0);
        if (!accept) {
            float prob = expf(-((float)delta) / T);
            accept = (curand_uniform(&rng) < prob);
        }

        if (accept) {
            energy = new_energy;
            c4 = new_c4; c8 = new_c8; c16 = new_c16; c32 = new_c32;

            if (energy < local_best_energy) {
                local_best_energy = energy;
                for (int i = 0; i < n; ++i) local_best_adj[i] = adj[i];
                last_improve_step = step;
            }

            if (energy == 0) {
                atomicExch(d_found_flag, 1);
                for (int i = 0; i < n; ++i) {
                    d_winning_adj[i] = adj[i];
                    d_all_best_adj[tid * n + i] = adj[i];
                }
                d_all_best_energy[tid] = 0;
                d_moves_evaluated[tid] = moves_evaluated;
                return;
            }
        } else {
            // Undo: drop the proposed edges, restore the original ones.
            adj[n1_a] &= ~(1ULL << n1_b); adj[n1_b] &= ~(1ULL << n1_a);
            adj[n2_a] &= ~(1ULL << n2_b); adj[n2_b] &= ~(1ULL << n2_a);
            if (move_type == 3) {
                adj[n3_a] &= ~(1ULL << n3_b); adj[n3_b] &= ~(1ULL << n3_a);
                adj[w] |= (1ULL << z); adj[z] |= (1ULL << w);
            }
            adj[u] |= (1ULL << v); adj[v] |= (1ULL << u);
            adj[x] |= (1ULL << y); adj[y] |= (1ULL << x);
        }
    }

    d_all_best_energy[tid] = local_best_energy;
    d_moves_evaluated[tid] = moves_evaluated;
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
                parsed_n = parsed_n * 10 + (json_str[k] - 48);
                k++;
            }
            if (parsed_n > 0) n = parsed_n;
        }
    }

    if (n <= 0 || n > MAX_V) return false;

    // Only the array following the "adj" key is read, so the value of "n" can never
    // be mistaken for graph data.
    adj_out.assign(n, 0);
    size_t adj_pos = json_str.find("\"adj\"");
    if (adj_pos == std::string::npos) return false;
    size_t start = json_str.find("[", adj_pos);
    if (start == std::string::npos) return false;

    const char OPEN = 91;   // [
    const char CLOSE = 93;  // ]

    int u = 0;
    size_t i = start + 1;
    while (i < json_str.size() && u < n) {
        while (i < json_str.size() && json_str[i] != OPEN && json_str[i] != CLOSE) i++;
        if (i >= json_str.size() || json_str[i] == CLOSE) break;
        i++; // step past the opening bracket

        while (i < json_str.size() && json_str[i] != CLOSE) {
            while (i < json_str.size() && !isdigit(json_str[i]) && json_str[i] != CLOSE) i++;
            if (i >= json_str.size() || json_str[i] == CLOSE) break;
            int v = 0;
            while (i < json_str.size() && isdigit(json_str[i])) {
                v = v * 10 + (json_str[i] - 48);
                i++;
            }
            if (u < n && v < n && u != v) {
                adj_out[u] |= (1ULL << v);
                adj_out[v] |= (1ULL << u);
            }
        }
        u++;
        if (i < json_str.size() && json_str[i] == CLOSE) i++;
    }
    return (u == n);
}

void print_usage(const char* prog) {
    std::cerr
        << "Usage: " << prog << " [n] [iterations] [options]\n\n"
        << "  n                 vertices (even, 4.." << MAX_N_SUPPORTED << "); default 32\n"
        << "  iterations        annealing steps per thread; default 2000\n"
        << "  --threads N       total CUDA threads; default 10240\n"
        << "  --temp T          initial temperature before the per-thread spread; default 4\n"
        << "  --count-cap N     max cycles counted per tier; default 1000000\n"
        << "  --stagnation N    steps without improvement before an ILS reheat; default 2000\n"
        << "  --seed-json JSON  start from this graph\n"
        << "  --seed-file PATH  start from the graph in this file (preferred: no argv limit)\n"
        << "  --json-only       emit only the result JSON\n\n"
        << "n > " << MAX_N_SUPPORTED << " is refused: at n = 64 the length 64 is itself a power\n"
        << "of two and this kernel has no C64 tier, so energy 0 would not mean\n"
        << "counterexample. Always confirm candidates with verifier_64.\n";
}

int main(int argc, char** argv) {
    int n = 32;
    int total_threads = 10240;
    int iterations = 2000;
    int count_cap = 1000000;
    int stagnation_limit = 2000;
    float initial_temp = 4.0f;
    bool json_only = false;
    std::string seed_json_str = "";

    // Positional arguments are the first two bare numbers in order, wherever the flags
    // appear. The old parser keyed off argv index, so "--json-only 32 50000" silently
    // set iterations = 32 and never set n.
    int positional_seen = 0;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--json-only") {
            json_only = true;
        } else if (arg == "--seed-json" && i + 1 < argc) {
            seed_json_str = argv[++i];
        } else if (arg == "--seed-file" && i + 1 < argc) {
            std::ifstream f(argv[++i]);
            if (!f.is_open()) {
                std::cerr << "Error: could not open seed file" << std::endl;
                return 2;
            }
            std::stringstream ss;
            ss << f.rdbuf();
            seed_json_str = ss.str();
        } else if (arg == "--threads" && i + 1 < argc) {
            total_threads = std::atoi(argv[++i]);
        } else if (arg == "--temp" && i + 1 < argc) {
            initial_temp = (float)std::atof(argv[++i]);
        } else if (arg == "--count-cap" && i + 1 < argc) {
            count_cap = std::atoi(argv[++i]);
        } else if (arg == "--stagnation" && i + 1 < argc) {
            stagnation_limit = std::atoi(argv[++i]);
        } else if (arg == "-h" || arg == "--help") {
            print_usage(argv[0]);
            return 0;
        } else if (!arg.empty() && isdigit(arg[0])) {
            if (positional_seen == 0) n = std::atoi(arg.c_str());
            else if (positional_seen == 1) iterations = std::atoi(arg.c_str());
            positional_seen++;
        } else {
            std::cerr << "Error: unknown argument " << arg << std::endl;
            print_usage(argv[0]);
            return 2;
        }
    }

    std::vector<uint64_t> seed_adj;
    int has_seed = 0;
    if (!seed_json_str.empty()) {
        if (!parse_seed_json(seed_json_str, n, seed_adj)) {
            std::cerr << "Error: could not parse the seed graph JSON" << std::endl;
            return 2;
        }
        has_seed = 1;
    }

    if (n < 4 || n % 2 != 0) {
        std::cerr << "Error: 3-regular graphs need an even vertex count >= 4" << std::endl;
        return 2;
    }
    if (n > MAX_N_SUPPORTED) {
        std::cerr << "Error: n = " << n << " exceeds " << MAX_N_SUPPORTED
                  << ". At n = 64 the length 64 is a power of two and this kernel has no "
                     "C64 tier, so energy 0 would not mean counterexample." << std::endl;
        return 2;
    }
    if (total_threads < 1 || count_cap < 1 || stagnation_limit < 1 || initial_temp <= 0.0f) {
        std::cerr << "Error: --threads, --count-cap, --stagnation, --temp must be positive"
                  << std::endl;
        return 2;
    }

    // Cool from initial_temp to about 1% of it across the whole run. The old fixed
    // 0.9997 rate froze long runs into greedy descent after a few thousand steps.
    float cooling_rate = (iterations > 1) ? powf(0.01f, 1.0f / (float)iterations) : 1.0f;

    if (!json_only) {
        std::cout << "=== Erdos #64 GPU Swarm Searcher ===" << std::endl;
        std::cout << "Vertices n: " << n << " | Threads: " << total_threads
                  << " | Iterations/Thread: " << iterations << std::endl;
        std::cout << "Initial temp: " << initial_temp << " | Cooling/step: " << cooling_rate
                  << " | Count cap: " << count_cap << std::endl;
        std::cout << "Mode: " << (has_seed ? "Seeded annealing" : "Stochastic search") << std::endl;
    }

    int* d_found_flag;
    int* d_all_best_energy;
    uint64_t* d_winning_adj;
    uint64_t* d_all_best_adj;
    unsigned long long* d_moves_evaluated;
    uint64_t* d_seed_adj = nullptr;

    cudaMalloc(&d_found_flag, sizeof(int));
    cudaMalloc(&d_all_best_energy, sizeof(int) * total_threads);
    cudaMalloc(&d_winning_adj, sizeof(uint64_t) * n);
    cudaMalloc(&d_all_best_adj, sizeof(uint64_t) * n * total_threads);
    cudaMalloc(&d_moves_evaluated, sizeof(unsigned long long) * total_threads);
    cudaMemset(d_moves_evaluated, 0, sizeof(unsigned long long) * total_threads);

    if (has_seed) {
        cudaMalloc(&d_seed_adj, sizeof(uint64_t) * n);
        cudaMemcpy(d_seed_adj, seed_adj.data(), sizeof(uint64_t) * n, cudaMemcpyHostToDevice);
    }

    cudaMemset(d_found_flag, 0, sizeof(int));

    int blockSize = 256;
    int numBlocks = (total_threads + blockSize - 1) / blockSize;

    auto start_time = std::chrono::high_resolution_clock::now();

    swarm_search_kernel<<<numBlocks, blockSize>>>(
        n, iterations, initial_temp, cooling_rate, count_cap, stagnation_limit,
        d_found_flag, d_winning_adj, d_all_best_energy, d_all_best_adj,
        d_moves_evaluated, d_seed_adj, has_seed
    );
    cudaError_t launch_err = cudaDeviceSynchronize();
    if (launch_err != cudaSuccess) {
        std::cerr << "CUDA error: " << cudaGetErrorString(launch_err) << std::endl;
        return 2;
    }

    auto end_time = std::chrono::high_resolution_clock::now();
    double duration_ms = std::chrono::duration<double, std::milli>(end_time - start_time).count();

    int h_found = 0;
    cudaMemcpy(&h_found, d_found_flag, sizeof(int), cudaMemcpyDeviceToHost);

    std::vector<int> h_energies(total_threads);
    cudaMemcpy(h_energies.data(), d_all_best_energy, sizeof(int) * total_threads, cudaMemcpyDeviceToHost);

    std::vector<unsigned long long> h_moves(total_threads);
    cudaMemcpy(h_moves.data(), d_moves_evaluated, sizeof(unsigned long long) * total_threads,
               cudaMemcpyDeviceToHost);

    int best_tid = 0;
    int h_best_energy = h_energies[0];
    for (int t = 1; t < total_threads; ++t) {
        if (h_energies[t] < h_best_energy) {
            h_best_energy = h_energies[t];
            best_tid = t;
        }
    }

    // Honest throughput: only moves whose energy was actually evaluated are counted.
    // The old figure was threads * iterations, which counted every loop iteration,
    // including the many that bailed out before proposing a valid swap.
    unsigned long long total_moves = 0;
    for (int t = 0; t < total_threads; ++t) total_moves += h_moves[t];

    std::vector<uint64_t> final_adj(n);
    if (h_found) {
        cudaMemcpy(final_adj.data(), d_winning_adj, sizeof(uint64_t) * n, cudaMemcpyDeviceToHost);
        h_best_energy = 0;
    } else {
        cudaMemcpy(final_adj.data(), d_all_best_adj + best_tid * n, sizeof(uint64_t) * n, cudaMemcpyDeviceToHost);
    }

    if (!json_only) {
        std::cout << "Swarm completed in " << duration_ms << " ms" << std::endl;
        std::cout << "Evaluated moves: " << total_moves << " ("
                  << (total_moves / (duration_ms / 1000.0) / 1e6)
                  << " million evaluated moves/sec)" << std::endl;
        std::cout << "Best energy reached in swarm: " << h_best_energy << std::endl;
        if (h_found) {
            std::cout << "Energy 0 reached. Confirm with verifier_64 before claiming anything."
                      << std::endl;
        }
    }

    std::cout << "{\"counterexample_candidate\":" << (h_found ? "true" : "false")
              << ",\"best_energy\":" << h_best_energy
              << ",\"evaluated_moves\":" << total_moves
              << ",\"duration_ms\":" << duration_ms
              << ",\"count_cap\":" << count_cap
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

    cudaFree(d_found_flag);
    cudaFree(d_all_best_energy);
    cudaFree(d_winning_adj);
    cudaFree(d_all_best_adj);
    cudaFree(d_moves_evaluated);
    if (d_seed_adj) cudaFree(d_seed_adj);

    return (h_found ? 0 : 1);
}
