"""Run the archived, host-free probes and capture output without overwriting results."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from importlib.metadata import version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--root', type=Path,
                        help='Checkout whose newton/ is measured (default: the one containing this script); '
                             'point it at a worktree of an older revision for before/after comparisons.')
    args = parser.parse_args()
    scripts = Path(__file__).resolve().parent
    root = (args.root or scripts.parents[2]).resolve()
    if not (root / 'newton' / 'worker.py').is_file():
        parser.error(f'No newton/worker.py under {root}.')
    output = args.output.resolve()
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error('Output must be a new or empty directory.')
    output.mkdir(parents=True, exist_ok=True)
    manifest = dict(
        started_utc=datetime.now(timezone.utc).isoformat(),
        python=sys.version,
        executable=sys.executable,
        platform=platform.platform(),
        machine=platform.machine(),
        processor=platform.processor(),
        repository=str(root),
        source_revision=subprocess.check_output(
            ['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip(),
        dependencies={name: version(name) for name in ('mujoco', 'numpy', 'PySide6')},
        source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in sorted((root / 'newton').glob('*.py'))},
        runs=[],
    )
    scratch = Path('/tmp/opencode')
    env = dict(os.environ, QT_QPA_PLATFORM='offscreen', PYTHONDONTWRITEBYTECODE='1')
    with tempfile.TemporaryDirectory(
            prefix='newton-review-', dir=scratch if scratch.is_dir() else None) as temp:
        for name in ('newton_perf_review.py', 'newton_perf_followup.py',
                     'newton_perf_ui_followup.py'):
            original = (scripts / name).read_bytes()
            source = original.decode('utf-8').replace(
                '/home/equinox/git/private/ingetrazo-newton', root.as_posix()).replace(
                '/tmp/opencode/newton-review-settings', Path(temp).as_posix())
            (output / f'{name}.executed.py').write_text(source, encoding='utf-8')
            run = subprocess.run(
                [sys.executable, '-B', '-'], input=source, cwd=root, env=env,
                capture_output=True, text=True, timeout=180)
            (output / f'{name}.stdout.txt').write_text(run.stdout, encoding='utf-8')
            (output / f'{name}.stderr.txt').write_text(run.stderr, encoding='utf-8')
            manifest['runs'].append(dict(
                script=name,
                original_sha256=hashlib.sha256(original).hexdigest(),
                executed_sha256=hashlib.sha256(source.encode()).hexdigest(),
                command=[sys.executable, '-B', '-'],
                returncode=run.returncode))
            print(f'{name}: exit {run.returncode}; output in {output}')
    manifest['finished_utc'] = datetime.now(timezone.utc).isoformat()
    (output / 'manifest.json').write_text(
        json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return int(any(run['returncode'] for run in manifest['runs']))


if __name__ == '__main__':
    raise SystemExit(main())
