// Simulated annealing for large uniform 3-sunflower-free families: one family per block.
//
// A lower bound on the sunflower-free capacity mu_3 needs a k-uniform family on [n] with
// no 3-sunflower, and nothing more -- the maximum is irrelevant, only whether a family of
// a given size exists. That is why this exists alongside the SAT sweep. SAT is built to
// prove (exact maxima, UNSAT certificates) and spends its budget establishing upper limits
// nobody needs; annealing proves nothing and finds things, which is the trade a lower
// bound wants.
//
// State per block: m masks, each of popcount k, all distinct, held in SHARED memory.
// Energy: the number of sunflower triples. Zero means the family is admissible.
// Move: thread 0 proposes moving one element of one member, in or out, so popcount stays
//       k and uniformity is structural rather than scored. The block then evaluates it
//       cooperatively.
//
// Why one family per block rather than per thread. The delta of a move touching member
// `idx` is the change in triples through `idx`, which is O(m^2) -- 2,415 pairs at m = 70.
// A per-thread family needs `uint64_t fam[MAX_MEMBERS]` twice over, 4 KB of local memory
// that is global-backed, and reads all of it serially on every move. Per block, the family
// sits in shared memory and the O(m^2) pairs divide across the block's threads.
//
// Each block writes its own best to its own output slot, so there is no cross-block race.
// An earlier version did `atomicMin` on a shared best and then copied, which is not atomic
// as a pair: two blocks could pass the guard and interleave writes, emitting a family that
// was a mixture of two different ones.
//
// Nothing here is ground truth. Whatever this reports is a candidate; the compiled Rust
// checker in ../verifier re-derives uniformity, distinctness and the exact triple count,
// and only that counts.
//
// Build: cuda\build.bat        (needs cl.exe on PATH; the script locates MSVC)
// Usage: swarm_857.exe <n> <k> <m> [--iters N] [--blocks N] [--block-size N]
//                      [--temp T] [--restart N] [--rng-seed S] [--json-only]

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <cstdint>
#include <curand_kernel.h>

#define MAX_MEMBERS 256

// Does the triple (a, b, c) have all three pairwise intersections equal? Equality of the
// three forces each to equal a & b & c, so the core is never computed.
__device__ __forceinline__ bool is_sunflower(uint64_t a, uint64_t b, uint64_t c) {
    const uint64_t ab = a & b;
    return ab == (a & c) && ab == (b & c);
}

// A uniformly random k-subset of [n], by partial Fisher-Yates. Thread 0 only.
__device__ uint64_t random_kset(curandState* st, int n, int k) {
    unsigned char perm[64];
    for (int i = 0; i < n; ++i) perm[i] = (unsigned char)i;
    for (int i = 0; i < k; ++i) {
        const int j = i + (int)(curand(st) % (unsigned)(n - i));
        const unsigned char t = perm[i];
        perm[i] = perm[j];
        perm[j] = t;
    }
    uint64_t mask = 0;
    for (int i = 0; i < k; ++i) mask |= (1ULL << perm[i]);
    return mask;
}

// Move one element of `mask`: clear a set bit, set a clear one. Popcount is preserved, so
// a move can never break uniformity.
__device__ uint64_t nudge(curandState* st, uint64_t mask, int n) {
    const uint64_t full = (n >= 64) ? ~0ULL : ((1ULL << n) - 1ULL);
    const uint64_t in_bits = full & ~mask;
    const int out_n = __popcll(mask);
    const int in_n = __popcll(in_bits);
    if (out_n == 0 || in_n == 0) return mask;

    // __fns finds the n-th set bit directly, avoiding a loop over the word.
    const uint32_t drop_pos = __fns(mask, 0, (int)(curand(st) % (unsigned)out_n) + 1);
    const uint32_t add_pos = __fns(in_bits, 0, (int)(curand(st) % (unsigned)in_n) + 1);
    if (drop_pos > 63 || add_pos > 63) return mask;
    return (mask & ~(1ULL << drop_pos)) | (1ULL << add_pos);
}

// Triples through `idx`, summed cooperatively across the block into *acc.
// Pairs (i, j) with i < j and both != idx are split by strided outer index.
__device__ void count_through(const uint64_t* fam, int m, int idx, int* acc) {
    const uint64_t v = fam[idx];
    int local = 0;
    for (int i = threadIdx.x; i < m; i += blockDim.x) {
        if (i == idx) continue;
        const uint64_t vi = v & fam[i];
        for (int j = i + 1; j < m; ++j) {
            if (j == idx) continue;
            if (vi == (v & fam[j]) && vi == (fam[i] & fam[j])) ++local;
        }
    }
    if (local) atomicAdd(acc, local);
}

// Whole energy, cooperatively. Used at initialisation and after a shake.
__device__ void count_all(const uint64_t* fam, int m, int* acc) {
    int local = 0;
    for (int i = threadIdx.x; i < m; i += blockDim.x) {
        for (int j = i + 1; j < m; ++j) {
            const uint64_t ij = fam[i] & fam[j];
            for (int l = j + 1; l < m; ++l)
                if (ij == (fam[i] & fam[l]) && ij == (fam[j] & fam[l])) ++local;
        }
    }
    if (local) atomicAdd(acc, local);
}

__device__ __forceinline__ bool duplicate(const uint64_t* fam, int m, int skip, uint64_t cand) {
    for (int i = 0; i < m; ++i)
        if (i != skip && fam[i] == cand) return true;
    return false;
}

__global__ void anneal(int n, int k, int m, int iters, float temp0,
                       int restart_after, unsigned long long seed,
                       uint64_t* best_out, int* best_energy) {
    extern __shared__ uint64_t shared_mem[];
    uint64_t* fam = shared_mem;                 // m masks, the working family
    uint64_t* best = shared_mem + m;            // m masks, the best seen in this block

    __shared__ int s_acc;          // cooperative accumulator
    __shared__ int s_energy;       // current energy
    __shared__ int s_best;         // best energy in this block
    __shared__ int s_idx;          // member the proposed move touches
    __shared__ uint64_t s_cand;    // proposed replacement
    __shared__ int s_valid;        // is the proposal worth evaluating
    __shared__ int s_before;
    __shared__ uint64_t s_old;     // the mask before the proposed move, for undo
    __shared__ int s_since;        // moves since the last improvement
                                   // MUST be shared: only thread 0 updates it, and
                                   // the restart branch below contains a barrier, so
                                   // a thread-local copy makes that branch divergent
                                   // and hangs the block.
    __shared__ curandState s_rng;

    const int bid = blockIdx.x;

    if (threadIdx.x == 0) {
        // Seeded per block and per run. A hardcoded seed made every restart bit-identical
        // in the sibling problem's kernel, which cost whole campaigns.
        curand_init(seed + (unsigned long long)bid * 0x9E3779B97F4A7C15ULL, bid, 0, &s_rng);
        for (int i = 0; i < m; ++i) {
            uint64_t cand;
            int guard = 0;
            do { cand = random_kset(&s_rng, n, k); }
            while (duplicate(fam, i, -1, cand) && ++guard < 256);
            fam[i] = cand;
        }
        s_acc = 0;
    }
    __syncthreads();

    count_all(fam, m, &s_acc);
    __syncthreads();

    if (threadIdx.x == 0) {
        s_energy = s_acc;
        s_best = s_acc;
        for (int i = 0; i < m; ++i) best[i] = fam[i];
    }
    __syncthreads();

    if (threadIdx.x == 0) s_since = 0;
    __syncthreads();

    for (int it = 0; it < iters; ++it) {
        if (s_best == 0) break;   // admissible: nothing left to find

        if (threadIdx.x == 0) {
            s_idx = (int)(curand(&s_rng) % (unsigned)m);
            const uint64_t cand = nudge(&s_rng, fam[s_idx], n);
            s_cand = cand;
            s_valid = (cand != fam[s_idx] && !duplicate(fam, m, s_idx, cand)) ? 1 : 0;
            s_acc = 0;
        }
        __syncthreads();

        if (!s_valid) { __syncthreads(); continue; }

        count_through(fam, m, s_idx, &s_acc);
        __syncthreads();

        if (threadIdx.x == 0) {
            s_before = s_acc;
            s_old = fam[s_idx];    // keep the pre-move mask so a reject can undo exactly
            fam[s_idx] = s_cand;   // apply provisionally
            s_acc = 0;
        }
        __syncthreads();

        count_through(fam, m, s_idx, &s_acc);
        __syncthreads();

        if (threadIdx.x == 0) {
            const int delta = s_acc - s_before;
            const float t = temp0 * (1.0f - (float)it / (float)iters) + 1e-3f;
            bool accept = delta <= 0;
            if (!accept) accept = curand_uniform(&s_rng) < __expf(-(float)delta / t);

            if (accept) {
                s_energy += delta;
                if (s_energy < s_best) {
                    s_best = s_energy;
                    for (int i = 0; i < m; ++i) best[i] = fam[i];
                    s_since = 0;
                } else {
                    ++s_since;
                }
            } else {
                fam[s_idx] = s_old;   // exact undo of the provisional write
                ++s_since;
            }
            s_acc = 0;
        }
        __syncthreads();

        if (s_since > restart_after) {
            if (threadIdx.x == 0) {
                for (int r = 0; r < 4; ++r) {
                    const int j = (int)(curand(&s_rng) % (unsigned)m);
                    uint64_t c;
                    int guard = 0;
                    do { c = random_kset(&s_rng, n, k); }
                    while (duplicate(fam, m, j, c) && ++guard < 64);
                    fam[j] = c;
                }
                s_acc = 0;
                s_since = 0;
            }
            __syncthreads();
            count_all(fam, m, &s_acc);
            __syncthreads();
            if (threadIdx.x == 0) s_energy = s_acc;
            __syncthreads();
        }
    }

    // Per-block output slot: no cross-block race by construction.
    if (threadIdx.x == 0) {
        best_energy[bid] = s_best;
        for (int i = 0; i < m; ++i) best_out[(size_t)bid * m + i] = best[i];
    }
}

int main(int argc, char** argv) {
    if (argc < 4) {
        fprintf(stderr,
            "usage: %s <n> <k> <m> [--iters N] [--blocks N] [--block-size N]\n"
            "          [--temp T] [--restart N] [--rng-seed S] [--json-only]\n", argv[0]);
        return 2;
    }
    const int n = atoi(argv[1]);
    const int k = atoi(argv[2]);
    const int m = atoi(argv[3]);

    int iters = 200000, blocks = 256, block_size = 128, restart_after = 2000;
    float temp = 2.0f;
    unsigned long long seed = 0x243F6A8885A308D3ULL;
    bool json_only = false;

    for (int i = 4; i < argc; ++i) {
        if (!strcmp(argv[i], "--iters") && i + 1 < argc) iters = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--blocks") && i + 1 < argc) blocks = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--block-size") && i + 1 < argc) block_size = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--temp") && i + 1 < argc) temp = (float)atof(argv[++i]);
        else if (!strcmp(argv[i], "--restart") && i + 1 < argc) restart_after = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--rng-seed") && i + 1 < argc) seed = strtoull(argv[++i], nullptr, 10);
        else if (!strcmp(argv[i], "--json-only")) json_only = true;
        else { fprintf(stderr, "unknown argument: %s\n", argv[i]); return 2; }
    }

    if (n < 1 || n > 64) { fprintf(stderr, "n must be in 1..64\n"); return 2; }
    if (k < 1 || k >= n) { fprintf(stderr, "k must be in 1..n-1\n"); return 2; }
    if (m < 3 || m > MAX_MEMBERS) {
        fprintf(stderr, "m must be in 3..%d\n", MAX_MEMBERS);
        return 2;
    }

    uint64_t* d_best = nullptr;
    int* d_energy = nullptr;
    cudaMalloc(&d_best, (size_t)blocks * m * sizeof(uint64_t));
    cudaMalloc(&d_energy, (size_t)blocks * sizeof(int));

    const size_t shmem = (size_t)2 * m * sizeof(uint64_t);

    if (!json_only) {
        fprintf(stderr,
            "n=%d k=%d m=%d | %d blocks x %d threads, %d iters, temp %.2f, "
            "seed %llu, %zu B shared/block\n",
            n, k, m, blocks, block_size, iters, temp, seed, shmem);
    }

    anneal<<<blocks, block_size, shmem>>>(n, k, m, iters, temp, restart_after, seed,
                                          d_best, d_energy);
    const cudaError_t err = cudaDeviceSynchronize();
    if (err != cudaSuccess) {
        fprintf(stderr, "kernel failed: %s\n", cudaGetErrorString(err));
        return 1;
    }

    int* energies = (int*)malloc((size_t)blocks * sizeof(int));
    uint64_t* fams = (uint64_t*)malloc((size_t)blocks * m * sizeof(uint64_t));
    cudaMemcpy(energies, d_energy, (size_t)blocks * sizeof(int), cudaMemcpyDeviceToHost);
    cudaMemcpy(fams, d_best, (size_t)blocks * m * sizeof(uint64_t), cudaMemcpyDeviceToHost);

    int win = 0;
    for (int b = 1; b < blocks; ++b) if (energies[b] < energies[win]) win = b;
    const int energy = energies[win];

    // The energy here is the kernel's own count: a search signal, not a result. Pipe the
    // family to ../verifier's `check` binary for the number that may be quoted.
    printf("{\"n\":%d,\"k\":%d,\"m\":%d,\"kernel_energy\":%d,\"solved\":%s,\"sets\":[",
           n, k, m, energy, energy == 0 ? "true" : "false");
    for (int i = 0; i < m; ++i)
        printf("%s%llu", i ? "," : "", (unsigned long long)fams[(size_t)win * m + i]);
    printf("]}\n");

    if (!json_only) {
        fprintf(stderr, energy == 0
            ? "kernel energy 0 -- verify with verifier/target/release/check\n"
            : "best kernel energy %d (not admissible)\n", energy);
    }

    free(energies);
    free(fams);
    cudaFree(d_best);
    cudaFree(d_energy);
    return energy == 0 ? 0 : 1;
}
