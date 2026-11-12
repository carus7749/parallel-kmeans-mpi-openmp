# Strong scaling: job 1033995

Original full archive retained privately; personal filesystem location omitted.

JSONL SHA256: f6d840d992614471d49f3aa64529a7ecb78a6c879270cd81e69b923d7610e5fd

Verified 90 JSONL measurements against individual stdout JSON files; all return codes zero. Each of 15 configurations has one warmup and five measured repeats. Warmups excluded from summary. Source full_suite.py, job.sh and launch.py match local copies. Speedup uses serial median loop time; efficiency divides by active ranks*threads, not 12 allocated cores. SSE relative range across all runs: 5.9745593e-14.

Single-node experiment; no inter-node scaling claim. Reported allocation usage is 12*269/3600 = 0.896667 core-hours. PBS final CPU time 456 seconds differs from output epilogue 288 seconds; retain both, do not conflate with allocation usage.

## Public data derivative

Command arrays and scheduler job_id fields were removed for privacy. All other JSON values, including every measurement and timing, are unchanged. The original JSONL hash above refers to the private unredacted input, not this derivative.

Public JSONL SHA256: ce9091ae83c4640ed48db7f19a5b9ed4353a27f2590a78e6ba2d66236a7a2d6d
