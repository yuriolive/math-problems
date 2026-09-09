.PHONY: all build-verifier build-cuda build-lean test test-rust test-python test-lean \
        search-gpu polish-gpu campaign search-sat audit-lean recount verify report paper paper-clean check-docs clean

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
	PYTHONPATH=. uv run python -m unittest discover -s tests

test-lean: build-lean

# Rule 8, mechanically: no `sorry` in any source, and every audited theorem resting
# on the three standard axioms only. Compiles against Mathlib, so it is slow cold.
audit-lean:
	cd ../../.. && uv run python tools/lean/audit.py problems/erdos/64/formalization-egc

# Stochastic GPU search. n must be even and <= 62: at n = 64 the length 64 is
# itself a power of two and the kernel has no C64 tier.
search-gpu:
	./cuda/swarm_64.exe 58 10000 --threads 10240

# Seeded polish of the saved candidate for one order.
polish-gpu:
	./cuda/swarm_64.exe 58 30000 --threads 10240 --seed-file cuda/f4_best_n58.json

# Multi-order GPU campaign, verified per order. Starts at the f(4) >= 54 floor:
# below 54 vertices no cubic counterexample exists, so smaller orders are empty.
campaign:
	uv run python campaign_solver.py

# Z3 search. Powers of two up to n are forbidden; short lengths are enumerated
# eagerly, longer ones handled by lazy cycle blocking against the Rust verifier.
search-sat:
	uv run python sat/run_sat.py 12

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
