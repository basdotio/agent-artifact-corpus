---
name: performance-engineering
description: Systems-level performance engineering for Rust, C/C++, and Python codebases. Use when profiling, debugging performance bottlenecks, analyzing CPU/memory usage, finding slow code paths, optimizing hot loops, investigating cache misses, analyzing compile times, or improving runtime performance. Triggers on queries about flamegraphs, perf, valgrind, profilers, benchmarking, or "why is this slow".
---

# Performance Engineering

Systems-level profiling and debugging for Rust, C/C++, and Python. Focus on finding what's slow, understanding why, and fixing it systematically.

## Core Philosophy

1. **Measure before optimizing** - Never guess where bottlenecks are
2. **Profile in release mode** - Debug builds hide real performance characteristics
3. **Isolate variables** - Change one thing at a time, measure impact
4. **Question the algorithm first** - O(n²) won't be saved by micro-optimizations
5. **Cache behavior matters** - Memory access patterns often dominate CPU time

## Quick Reference: Tool Selection

| Problem | Linux | macOS | Tool |
|---------|-------|-------|------|
| CPU hotspots | `perf record` | `Instruments` | flamegraph |
| Memory leaks | `valgrind --leak-check=full` | `leaks` | heaptrack |
| Cache misses | `perf stat -e cache-misses` | `Instruments` | cachegrind |
| Syscall overhead | `strace -c` | `dtruss` | - |
| I/O bottlenecks | `perf trace` | `fs_usage` | - |
| Lock contention | `perf lock` | `Instruments` | - |
| Compile time | `-ftime-trace` (Clang) | same | ClangBuildAnalyzer |

## Profiling Workflow

### Step 1: Establish Baseline

Before any investigation, capture reproducible baseline metrics:

```bash
# Create benchmark script that exercises the slow path
# Run 3-5 times, record median

# Rust
hyperfine --warmup 3 'cargo run --release -- <args>'

# C/C++
hyperfine --warmup 3 './build/release/program <args>'

# Python
hyperfine --warmup 3 'python script.py <args>'
```

Record: wall time, peak memory (via `/usr/bin/time -v`), and relevant counters.

### Step 2: CPU Profiling

#### Linux (perf + flamegraph)

```bash
# Record profile (Rust/C/C++)
perf record -g --call-graph dwarf ./target/release/program

# Generate flamegraph
perf script | stackcollapse-perf.pl | flamegraph.pl > flame.svg

# Quick interactive analysis
perf report
```

#### macOS (Instruments or samply)

```bash
# samply (recommended for Rust/C++)
samply record ./target/release/program
# Opens Firefox Profiler automatically

# Instruments CLI
xcrun xctrace record --template 'Time Profiler' --launch ./program
```

#### Rust-Specific CPU Profiling

```bash
# cargo-flamegraph (simplest)
cargo flamegraph -- <args>

# With debug symbols in release
# Add to Cargo.toml:
# [profile.release]
# debug = true

# For async code, use tokio-console
RUSTFLAGS="--cfg tokio_unstable" cargo build
tokio-console
```

#### C/C++ with gprof

```bash
# Compile with profiling
gcc -pg -O2 -g program.c -o program
./program
gprof program gmon.out > analysis.txt
```

#### Python Profiling

```bash
# cProfile (built-in)
python -m cProfile -s cumtime script.py > profile.txt

# py-spy (sampling profiler, no code changes)
py-spy record -o profile.svg -- python script.py

# line_profiler (line-by-line)
# Add @profile decorator to functions
kernprof -l -v script.py

# memory_profiler
python -m memory_profiler script.py
```

### Step 3: Memory Profiling

#### Heap Allocation Analysis

```bash
# Linux - heaptrack (recommended)
heaptrack ./program
heaptrack_gui heaptrack.program.*.gz

# Linux - valgrind massif
valgrind --tool=massif ./program
ms_print massif.out.*

# macOS
leaks --atExit -- ./program
```

#### Rust Memory

```bash
# DHAT (requires nightly for best results)
cargo install dhat
# Add to code: #[global_allocator] static ALLOC: dhat::Alloc = dhat::Alloc;

# Tracking allocations
RUST_LOG=trace cargo run 2>&1 | grep -i alloc
```

### Step 4: Cache & Memory Access Analysis

```bash
# Cache miss statistics
perf stat -e cache-references,cache-misses,L1-dcache-load-misses ./program

# Detailed cache simulation
valgrind --tool=cachegrind ./program
cg_annotate cachegrind.out.*

# Memory bandwidth
perf stat -e LLC-loads,LLC-load-misses,LLC-stores ./program
```

### Step 5: Identifying Specific Bottlenecks

#### Finding Hot Functions

```bash
# Top CPU consumers
perf report --sort=comm,dso,symbol --stdio | head -50

# Annotate specific function with source
perf annotate <function_name>
```

#### Finding Slow System Calls

```bash
# Linux
strace -c ./program                    # Summary
strace -T ./program 2>&1 | sort -k1 -r # By duration

# macOS
sudo dtruss ./program 2>&1 | head -100
```

#### Lock Contention (C/C++/Rust)

```bash
# Linux
perf lock record ./program
perf lock report

# Mutex contention in Rust
# Use parking_lot with deadlock_detection feature
```

## Language-Specific Techniques

### Rust Performance

**Compile-time optimization:**
```toml
# Cargo.toml
[profile.release]
lto = "fat"           # Link-time optimization
codegen-units = 1     # Better optimization, slower compile
panic = "abort"       # Smaller binary
```

**Runtime investigation:**
```bash
# Check for unexpected dynamic dispatch
cargo asm <crate>::<function>

# Bounds check elimination verification
RUSTFLAGS="-C target-cpu=native" cargo build --release

# Compile time analysis
cargo build --timings
```

**Common Rust bottlenecks:**
- Unnecessary `.clone()` in hot paths
- `Vec` reallocations (use `with_capacity`)
- String formatting in loops (use `write!` to buffer)
- Iterator vs loop (usually equivalent, but verify)
- `Rc`/`Arc` overhead (consider arena allocation)

### C/C++ Performance

**Compiler optimization flags:**
```bash
# GCC/Clang release build
-O3 -march=native -flto -ffast-math  # Aggressive
-O2 -march=native                     # Safe default

# Profile-guided optimization
gcc -fprofile-generate -O2 program.c -o program
./program <typical_workload>
gcc -fprofile-use -O2 program.c -o program_optimized
```

**Common C/C++ bottlenecks:**
- Cache-unfriendly data structures (AoS vs SoA)
- Unnecessary copies (missing move semantics)
- Virtual function overhead in hot paths
- False sharing in multithreaded code
- Unaligned memory access

**Analyzing generated assembly:**
```bash
# Compiler Explorer locally
objdump -d -S -C ./program | less

# Specific function
objdump -d ./program | awk '/<function_name>:/,/^$/'

# With source interleaving
gcc -g -O2 -fverbose-asm -S -o program.s program.c
```

### Python Performance

**Finding slow code:**
```bash
# Deterministic profiling
python -m cProfile -s tottime script.py 2>&1 | head -30

# Sampling (lower overhead)
py-spy top --pid <PID>
```

**Common Python bottlenecks:**
- Loops that should be NumPy vectorized
- Repeated attribute lookups in loops
- Creating objects in hot paths
- Global variable access (slower than local)
- String concatenation (use `''.join()`)

**Solutions:**
```python
# Move to C extensions for hot paths
# Use Cython for gradual optimization
# Consider PyPy for CPU-bound pure Python
# NumPy/Pandas for numerical work
```

## Compile Time Analysis

### Rust Compile Times

```bash
# Build timing breakdown
cargo build --timings

# Self-profiling (detailed)
RUSTFLAGS="-Z self-profile" cargo +nightly build --release
# Analyze with crox or summarize

# Find expensive derives/macros
cargo llvm-lines | head -30
```

### C/C++ Compile Times

```bash
# Clang time trace
clang++ -ftime-trace -c file.cpp
# Opens chrome://tracing or use ClangBuildAnalyzer

# Include analysis
include-what-you-use file.cpp

# Precompiled headers impact
time clang++ -x c++-header header.h -o header.pch
```

## Debugging Performance Regressions

### Git Bisect for Performance

```bash
# Create benchmark script
cat > bench.sh << 'EOF'
#!/bin/bash
cargo build --release 2>/dev/null || exit 125
result=$(hyperfine --warmup 1 --runs 3 './target/release/prog' --export-json /tmp/bench.json 2>/dev/null)
median=$(jq '.results[0].median' /tmp/bench.json)
threshold=1.5  # seconds
(( $(echo "$median > $threshold" | bc -l) )) && exit 1 || exit 0
EOF
chmod +x bench.sh

git bisect start
git bisect bad HEAD
git bisect good v1.0.0
git bisect run ./bench.sh
```

### A/B Comparison

```bash
# Compare two commits
git stash
hyperfine --warmup 3 './target/release/prog' --export-json baseline.json

git checkout <other-commit>
cargo build --release
hyperfine --warmup 3 './target/release/prog' --export-json comparison.json

# Statistical comparison
hyperfine --warmup 3 \
  -n baseline './baseline_binary' \
  -n candidate './candidate_binary'
```

## Reference Files

For detailed tool-specific guides, see:
- `references/flamegraph-guide.md` - Interpreting flamegraphs and common patterns
- `references/perf-events.md` - Hardware performance counters and their meanings
- `references/optimization-patterns.md` - Common optimizations by language

## Checklist: Before Claiming "Optimized"

1. [ ] Baseline measurement recorded with variance
2. [ ] Profiled in release/optimized mode
3. [ ] Identified actual bottleneck (not assumed)
4. [ ] Optimization targets the bottleneck
5. [ ] Post-optimization measurement shows improvement
6. [ ] No correctness regressions (tests pass)
7. [ ] Improvement documented with numbers
