# Archival verification — separate from the original review

Run on 6 November 2026, 10:56:11–10:56:24 UTC, using `scripts/run.py`. Exact environment, source hashes, commands and exit codes: [manifest](verification/manifest.json).

All three scripts exited successfully (0); the vectorized force assertions passed. Complete stdout, stderr and the executed source are retained under `verification/`. Offscreen Qt emitted `propagateSizeHints()` warnings, retained in stderr. No full application or host-dependent test suite was run.

| Probe | Verification result |
| --- | --- |
| 100 free bodies, baseline / damping / all attracting | 0.203 / 8.000 / 370.588 ms per eight-step batch |
| 100 attracting bodies, original / summed / vectorized follow-up | 385.677 / 188.756 / 14.220 ms |
| Vectorized force comparison | Passed at `rtol=atol=1e-12`; scalar maximum difference 0.0 |
| 100 constant telemetry labels, original / cached styles | 2.515 / 0.207 ms |
| 100 changing telemetry labels, original / cached styles | 2.494 / 1.384 ms |
| 1,000 collider paint, original / UID index | 31.809 / 21.248 ms |
| 250,000 unused simple vertices, JSON encode / decode | 80.865 / 58.493 ms; 4,250,212 bytes |
| Fake 500 ms shutdown wait | 500.082 ms, deliberately injected delay, not a real process measurement |

These reruns support the same bottleneck ranking but do not replace the original figures. Median variation is expected; the 10-label UI result in particular differed from the earlier run. Profiled attraction took 541 ms in this verification versus about 400 ms in the retained original record; profiling overhead and host load are reasons not to treat profile duration as the unprofiled runtime.

No production code or model changes are part of the archive. Source/script checksums and documentation links are validated before commit; the full host-dependent suite remains intentionally excluded.
