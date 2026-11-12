# Public derivative and verification

The three formal JSONL datasets contain 270 records, including warmups. Only `command` and `job_id` metadata fields were removed. All measured values and other JSON fields are preserved. Original full records and evidence hashes remain private; per-dataset provenance identifies both original and derivative hashes.

The C++ source, headers, tests, PBS scripts and experiment runners match the original project. Figures are unchanged. The public report source removes the student ID and internal hostname; the private assessment version retains them. Build output uses a neutral filename. The AI disclosure is unchanged.

SHA256SUMS.txt covers the intended public files. Verify from the repository root with `shasum -a 256 -c SHA256SUMS.txt` (macOS) or `sha256sum -c SHA256SUMS.txt` (Linux).

Generated Atlas logs can include personal paths and scheduler metadata. Keep them private; the default .gitignore excludes run and submission directories. Review any new files before publishing.
