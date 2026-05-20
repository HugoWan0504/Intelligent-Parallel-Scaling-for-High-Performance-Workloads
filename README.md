# Intelligent Parallel Scaling for High-Performance Workloads

This project studies how thread count affects the performance of a shared-memory parallel workload. The main workload is dense matrix multiplication.

The project compares four implementations:

1. Sequential baseline
2. Static Pthread version
3. Dynamic Pthread version
4. Optimized Pthread version with cache blocking