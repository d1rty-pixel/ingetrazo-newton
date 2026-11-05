# Scripts

Run from the repository root with the project's Python, for example `.venv/bin/python scripts/dev/preview.py`.

| Where | What |
|---|---|
| `scripts/` | Everyday tools: `install-local.sh` / `install-local.ps1` (copy the extension into IngeTrazo, see [docs/installation.md](../docs/installation.md)), `setup-runtime.ps1` (Windows runtime, see [docs/runtime-setup.md](../docs/runtime-setup.md)), `package.py` (release zip). |
| `scripts/dev/` | Developer tools: `preview.py` (test window with a demo), `icons.py` (icon export and overview sheet). |
| `scripts/models/` | Builders for the example and test models in `models/`; most take `--open` or `--existing`. Tests import their `build()` functions. |
| `scripts/lab/` | Measurements and audits: `benchmark_newton.py`, `benchmark_overlays.py`, `audit_contacts.py`. Results worth keeping go to `docs/lab/test-and-measurement-runs.md`. |
