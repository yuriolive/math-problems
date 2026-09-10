.PHONY: all build-verifier test test-rust test-python check-docs verify full clean

all: build-verifier

build-verifier:
	cd verifier && cargo build --release

test: test-rust test-python

test-rust:
	cd verifier && cargo test --release

# Differential tests against the independent Python reference. Builds the binary first if
# it is missing, so a pass here is never a pass by absence.
test-python:
	uv run python -m unittest discover -s tests

# Check one instance, e.g. make verify FILE=instances/k4-d3.json
verify:
	./verifier/target/release/ghzcheck $(FILE)

# The largest instance for a given (n, d): every colour slot present, all weights 1.
# make full N=6 D=3
N ?= 6
D ?= 3
full:
	uv run python tools/full_support.py $(N) $(D) > /tmp/k$(N)-d$(D)-full.json
	./verifier/target/release/ghzcheck /tmp/k$(N)-d$(D)-full.json --max-matchings 100000000

check-docs:
	cd ../../.. && uv run python tools/check_docs.py

clean:
	cd verifier && cargo clean
