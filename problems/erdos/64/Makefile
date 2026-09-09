.PHONY: all build-verifier build-cuda build-lean test test-rust test-python test-lean \
        search-gpu polish-gpu search-pes search-sat search-islands recount verify report paper paper-clean check-docs clean

all: build-verifier build-cuda

build-verifier:
	cargo build --release

# Uses cuda/build.bat, which locates vcvars64.bat itself. Override the target
# architecture with CUDA_ARCH=sm_86 (default is sm_89, Ada / RTX 40 series).
build-cuda:
	cmd /c "cuda\build.bat"

build-lean:
	cd formalization && lake build

test: test-rust test-python

test-rust:
	cargo test --release

test-python:
	uv run python -m unittest discover -s tests

test-lean: build-lean

# Stochastic GPU search. n must be even and <= 62: at n = 64 the length 64 is
# itself a power of two and the kernel has no C64 tier.
search-gpu:
	./cuda/swarm_64.exe 58 10000 --threads 10240

# Seeded polish of the saved candidate for one order.
polish-gpu:
	./cuda/swarm_64.exe 58 30000 --threads 10240 --seed-file cuda/f4_best_n58.json

# PES loop (Plan -> Execute -> Summarize) driven by the local `agy` CLI.
# Defaults start at n = 54: the literature's f(4) >= 54 means no cubic
# counterexample exists below 54 vertices, so any smaller order is provably empty.
search-pes:
	uv run python -m engine.loongflow_main --iterations 10 --test-ns 54,56,58

# Z3 search. Powers of two up to n are forbidden; short lengths are enumerated
# eagerly, longer ones handled by lazy cycle blocking against the Rust verifier.
search-sat:
	uv run python sat/run_sat.py 12

search-islands:
	uv run python engine/main.py --test-ns 54,56 --islands 5 --iterations 10

# Regenerates the candidate table in README section 5 from the actual verifier.
recount:
	uv run python tools/recount_candidates.py --cap 100000

# Verify one graph file, e.g. make verify FILE=cuda/best_swarm_n36.json
verify:
	uv run python tools/verify_graph.py $(FILE) --cap 100000

report:
	uv run python engine/report.py

clean:
	cargo clean
	cd formalization && lake clean

# Build the paper to PDF via the shared pipeline in tools/paper.
paper:
	cd ../../.. && uv run python tools/paper/build.py problems/erdos/64/paper

paper-clean:
	cd ../../.. && uv run python tools/paper/build.py problems/erdos/64/paper --clean

check-docs:
	cd ../../.. && uv run python tools/check_docs.py
