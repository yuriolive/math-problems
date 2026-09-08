.PHONY: all build-verifier build-cuda test run report clean

all: build-verifier build-cuda

build-verifier:
	cargo build --release

build-cuda:
	cmd /c "call \"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat\" && nvcc -O3 -std=c++17 -arch=sm_89 cuda/verifier_cuda.cu -o cuda/verifier_cuda.exe"

test:
	cargo test
	uv run python -m unittest discover -s tests

run:
	uv run python engine/main.py --n-eval 20 --islands 5

report:
	uv run python engine/report.py

clean:
	cargo clean
