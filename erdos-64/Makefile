.PHONY: all build-verifier build-cuda test search-gpu search-sat search-fun report clean

all: build-verifier build-cuda

build-verifier:
	cargo build --release

build-cuda:
	cmd /c "call \"C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat\" && nvcc -O3 -std=c++17 -arch=sm_89 cuda/swarm_64.cu -o cuda/swarm_64.exe"

test:
	cargo test
	uv run python -m unittest discover -s tests

search-gpu:
	./cuda/swarm_64.exe 32 10000

search-pes:
	uv run python -m engine.loongflow_main --iterations 10 --test-ns 32,34,36

search-sat:
	uv run python sat/run_sat.py 12

search-fun:
	uv run python engine/main.py --test-ns 24,32 --islands 5 --iterations 10

report:
	uv run python engine/report.py

clean:
	cargo clean
