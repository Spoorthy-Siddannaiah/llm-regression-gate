"""Test the uncommitted release source in isolation; never commit or configure remotes."""
import argparse
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='New directory, preferably in /tmp')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or output.is_relative_to(ROOT):
        parser.error('snapshot output must be outside the project')
    output.mkdir(parents=True, exist_ok=False)
    workspace = output / 'source'
    workspace.mkdir()
    files = subprocess.check_output(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT).decode().split('\0')
    for name in sorted(set(files) - {''}):
        source = ROOT / name
        if source.is_symlink():
            raise ValueError('release snapshot refuses symlink inputs')
        if not source.is_file():
            raise ValueError(f'missing release input: {name}')
        destination = workspace / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    # Tests inspect Git provenance. Copy existing metadata without Git writes,
    # history changes, or configuring a new origin/remote in either location.
    if not (ROOT / '.git').is_dir():
        raise ValueError('this verification helper requires ordinary directory-based Git metadata')
    shutil.copytree(ROOT / '.git', workspace / '.git')
    uv = shutil.which('uv')
    if uv is None:
        raise ValueError('uv must already be installed')
    subprocess.run([uv, 'sync', '--python', '3.12.13', '--locked'], cwd=workspace, check=True)
    python = workspace / '.venv/bin/python'
    subprocess.run([str(python), '-m', 'pytest', '-q', '-p', 'no:cacheprovider'], cwd=workspace, check=True)
    subprocess.run([str(python), 'scripts/verify_replays.py', '--output-dir', str(output / 'replays')], cwd=workspace, check=True)
    print(f'Isolated source snapshot verified: {workspace}')
    print('This tests uncommitted source plus copied existing history, not a new committed checkout.')


if __name__ == '__main__':
    main()
