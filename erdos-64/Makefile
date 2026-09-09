.PHONY: all build-verifier build-cuda build-lean test test-rust test-python test-lean \
        search-gpu search-pes search-sat search-islands recount verify report clean

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
	./cuda/swarm_64.exe 36 10000 --threads 10240

# Seeded polish of the saved candidate for one order.
polish-gpu:
	./cuda/swarm_64.exe 36 30000 --threads 10240 --seed-file cuda/best_swarm_n36.json

# PES loop (Plan -> Execute -> Summarize) driven by the local `agy` CLI.
# Defaults start at n = 36: every general cubic graph up to n = 34 is already
# excluded by exhaustive search.
search-pes:
	uv run python -m engine.loongflow_main --iterations 10 --test-ns 36,38,40

# Z3 search. Powers of two up to n are forbidden; short lengths are enumerated
# eagerly, longer ones handled by lazy cycle blocking against the Rust verifier.
search-sat:
	uv run python sat/run_sat.py 12

search-islands:
	uv run python engine/main.py --test-ns 36,38 --islands 5 --iterations 10

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
