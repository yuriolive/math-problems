.PHONY: all build-verifier test run report clean

all: build-verifier

build-verifier:
	cargo build --release

test:
	cargo test
	python -m unittest discover -s tests

run:
	python engine/main.py --n-eval 20 --islands 5

report:
	python engine/report.py

clean:
	cargo clean
