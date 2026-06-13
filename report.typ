#import "@preview/charged-ieee:0.1.4": ieee

#show: ieee.with(
  title: [Intelligent Parallel Scaling for High Performance Workloads],
  abstract: [
    Choosing the optimal number of threads for parallel workloads is a non-trivial task due to varying hardware characteristics, workload sizes, and synchronization overheads. In this project, we implement an intelligent parallel scaling framework that automatically selects the best thread count for high-performance workloads such as dense matrix multiplication and password cracking. Our framework uses a dynamic tuner that samples performance on a subset of the workload to predict the optimal configuration based on either performance or efficiency goals. We compare our autotuning approach against static thread assignments using OpenMP. Results demonstrate that our dynamic tuner can effectively identify near-optimal thread counts, balancing raw speedup with computational efficiency.
  ],
  authors: (
    (
      name: "Adil Mohiuddin",
      location: [University of California, Riverside],
    ),
    (
      name: "Sachin Chopra",
      location: [University of California, Riverside],
    ),
    (
      name: "Hugo Wan",
      location: [University of California, Riverside]
    ),
  ),
  index-terms: ("Parallel Computing", "Autotuning", "OpenMP", "Performance Analysis", "Matrix Multiplication"),
  bibliography: bibliography("refs.bib"),
  figure-supplement: [Fig.],
)

= Introduction
The increasing prevalence of multi-core processors has made parallel programming essential for high-performance computing. However, simply increasing the thread count does not always lead to better performance. Factors such as cache contention, synchronization overhead, and Amdahl's Law limit the scalability of many algorithms. Selecting the "right" number of threads often requires manual benchmarking on specific hardware, which is not portable. In this project we are examining embarrassingly parallel workloads (matrix multiplication and brute force password cracking). Although we did not do a roofline analysis on these workloads, we can confidently assume that these are compute bound rather than memory bounded problems (at least for large matrices). We show that our dynamic tuner can handle these 2 embarrassingly parallel workloads to show as a proof of concept that our dynamic tuner can work can used to find a optimal number of threads to run the application. We believe that the tuner is most useful for workloads where the parallelized code needs to run several times within a project/program (i.e. matrix multiplication in neural network training).

= Background
Parallel frameworks like OpenMP #cite(<dagum1998openmp>) provide tools for loop parallelization, but they often default to using all available cores. This can be sub-optimal for small problem sizes or memory-bound kernels. Automatic performance tuning (autotuning) #cite(<vuduc2005statistical>) addresses this by searching for optimal parameters at runtime or install-time.

One of the primary challenges in parallel computing is achieving good scalability as the number of threads increases. While additional threads can reduce execution time by distributing work across multiple cores, performance gains eventually diminish due to synchronization overhead, thread management costs, cache contention, and load imbalance. Furthermore, according to Amdahl's Law, the serial portion of an application limits the maximum achievable speedup regardless of the number of available cores.

Modern processors also introduce architectural complexities that affect parallel performance. Shared cache hierarchies, memory bandwidth limitations, simultaneous multithreading (SMT), and operating system scheduling decisions can all influence the optimal thread count for a given workload. As a result, the best-performing configuration often depends on both the application characteristics and the underlying hardware platform.



= Approach
We developed a generic `DynamicTuner` class that can be integrated into different workloads. The tuner operates in two main modes:
1. *Performance Goal*: Selects the thread count that achieves the lowest execution time on a sample problem.
2. *Efficiency Goal*: Selects the highest thread count that maintains a specified efficiency threshold (e.g., within 25% of the fastest runtime but with fewer threads).

Our implementation uses OpenMP for the parallel backend, ensuring a consistent runtime environment for both static and dynamic thread selections.

= Experimental Methodology
We evaluated our approach on two distinct workloads:
- *Dense Matrix Multiplication*: A compute-intensive kernel $(C = A times B)$.
- *Password Cracking*: A CPU-intensive brute-force search workload.

Benchmarks were conducted with varying matrix sizes ($128 times 128$, $256 times 256$) and thread counts ($1, 2, 4$). The dynamic tuner used a sample size of 2048 for matrix multiplication and a reduced search space for password cracking.

= Results & Analysis 

== Matrix Multiplication Performance
Figures 1 and 2 show the speedup and efficiency for matrix multiplication with $N=256$.

#figure(
  image("plots/openmp_scaling/speedup_N256.png", width: 100%),
  caption: [Speedup for $256 times 256$ Matrix Multiplication],
) <fig-speedup-256>

#figure(
  image("plots/openmp_scaling/efficiency_N256.png", width: 100%),
  caption: [Efficiency for $256 times 256$ Matrix Multiplication],
) <fig-eff-256>

As seen in @fig-speedup-256, the dynamic tuner successfully picks a thread count that matches or closely follows the peak performance of the static runs. The efficiency plot (@fig-eff-256) highlights how the "efficiency goal" can save resources by avoiding over-provisioning when returns are diminishing.

== Password Cracking Performance
The password cracking workload shows different scaling characteristics due to its search-based nature.

#figure(
  image("plots/password_crack/speedup_length6.png", width: 100%),
  caption: [Speedup for Password Cracking (Length 6)],
) <fig-pwd-speedup>

#figure(
  image("plots/password_crack/efficiency_length6.png", width: 100%),
  caption: [Efficiency for Password Cracking (Length 6)],
) <fig-pwd-eff>

The results in @fig-pwd-speedup and @fig-pwd-eff indicate that the workload scales well up to the available physical cores, and the dynamic tuner correctly identifies the trend while maintaining high efficiency.

= Conclusion & Lessons Learned
Our intelligent parallel scaling framework effectively automates the selection of thread counts. We learned that while "performance" goals are straightforward, "efficiency" goals require careful tuning of thresholds to avoid selecting too few threads. Future work could involve more sophisticated sampling techniques and support for heterogeneous architectures.

= Contributions
All team members contributed about the same amount to the final project. Hugo Wan ideated and created the baseline implementation, Adil Mohiuddin focused on the OpenMP integration, Sachin Chopra developed the dynamic tuner logic infrastructure.