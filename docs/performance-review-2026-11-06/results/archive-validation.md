# Archive validation

Checks before commit:

```text
PASS: source/model hashes, exact original-script copies, Python syntax, JSON, documentation links, three successful verification runs and executed-source hashes
```

- All eleven reviewed/supporting source hashes match `source-manifest.json`.
- Both user-modified model hashes match the values recorded before archival; neither model is staged.
- The three permanent probe scripts match their temporary originals byte-for-byte.
- All archived Python sources parse, all JSON files load, and relative links in the archive's Markdown files resolve.
- All three verification runs returned 0, and each saved executed source matches its recorded hash.
- No production code, model or host changes are staged.
- The full host-dependent pytest suite was not run, respecting the extension-only/host-exclusion constraint.

The standard staged whitespace check reports intentional historical formatting: Markdown hard-break spaces in `transcript/review-response-de.txt` and the final blank lines printed by `pstats` in `results/verification/newton_perf_review.py.stdout.txt`. These are retained rather than silently altering the transcript or raw log. The whitespace check for all other staged files passes; a second complete check with only blank-at-EOL/EOF warnings disabled also passes.
