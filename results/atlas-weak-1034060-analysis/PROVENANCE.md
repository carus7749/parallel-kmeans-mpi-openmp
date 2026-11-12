# Weak scaling: 1034060

Original full archive retained privately; personal filesystem location omitted.

SHA256: 987b4e30312ff1dc2d3b1df078a1c586498538e30b350829591f628bf11d01d4

54 records checked against individual stdout; all return codes zero. Nine configurations each have one warmup and five measured repeats. No outlier exclusions. Local job.sh/full_suite.py/launch.py match source snapshot. All inputs have 250000 rows per active core, d=16, K=8, 50 fixed iterations. Baselines are separate: MPI 1x1 (1 core), hybrid 1x2 (2 cores). Efficiency is baseline median loop time / configuration median loop time. SSE must not be compared across different N.

PBS walltime 215 seconds; allocation usage 12*215/3600=0.716667 core-hours. Final PBS cput=355 seconds; epilogue cput=287 seconds. Preserve both accounting readings.

## Public data derivative

Command arrays and scheduler job_id fields were removed for privacy. All other JSON values, including every measurement and timing, are unchanged. The original JSONL hash above refers to the private unredacted input, not this derivative.

Public JSONL SHA256: 49de96bf6debb6df27ab55dab13a14670a7b476be65b653fe6adc764a371cee8
