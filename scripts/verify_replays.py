"""Replay the eight public CI examples offline; no model calls or baseline writes."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True, help='New directory only')
    args = parser.parse_args()
    output = args.output_dir.resolve()
    try:
        output.mkdir(parents=True, exist_ok=False)
        baseline_dir = ROOT / 'recordings/squad/llama3.2-bm25-v1'
        expected = json.loads((ROOT / 'benchmarks/squad-top1-experiment-v1.json').read_text())['baseline_file_sha256']
        def baseline_hashes():
            return {str(p.relative_to(baseline_dir)): hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in baseline_dir.rglob('*') if p.is_file()}
        if baseline_hashes() != expected:
            raise ValueError('original baseline integrity check failed')
        for name, real, candidate, policy, status, codes in [
            ('accepted', False, 'candidate.synthetic.v1.json', 'synthetic.v1', 0, set()),
            ('intentional-regression', False, 'candidate.synthetic.v2.json', 'synthetic.v1', 1,
             {'below_minimum', 'excessive_drop', 'critical_facts_missing'}),
            ('squad-baseline', True, 'llama3.2-bm25-v1', 'relative-only.v1', 0, set()),
            ('squad-regression', True, 'llama3.2-bm25-top1-v1', 'relative-only.v1', 1, {'excessive_drop'}),
            ('v2-accepted', False, 'candidate.synthetic.v1.json', 'citation-v2', 0, set()),
            ('v2-absolute-failure', True, 'llama3.2-bm25-v1', 'citation-v2', 1, {'unknown_citation_limit'}),
            ('v2-real-regression', True, 'llama3.2-bm25-top1-v1', 'citation-v2', 1, {'excessive_drop'}),
            ('citation-enum', True, 'llama3.2-bm25-citation-enum-v2', 'citation-v2', 0, set()),
        ]:
            dataset = ROOT / ('datasets/squad/v1/dataset.json' if real else 'datasets/support_policy/v1/dataset.json')
            baseline = baseline_dir / 'recording.json' if real else ROOT / 'recordings/baseline.synthetic.v1.json'
            target = ROOT / 'recordings/squad' / candidate / 'recording.json' if real else ROOT / 'recordings' / candidate
            command = [sys.executable, '-m', 'llm_reliability', '--dataset', str(dataset), '--baseline', str(baseline),
                       '--candidate', str(target), '--policy', str(ROOT / f'configs/gate.{policy}.json'),
                       '--settings', str(ROOT / 'configs/evaluator.v1.json'), '--output-dir', str(output / name)]
            if real:
                command += ['--sources', str(dataset.with_name('sources.json')), '--require-manifests']
            if name == 'citation-enum':
                command += ['--expected-candidate-code', str(target.with_name('expected-code.json'))]
            process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=120)
            if process.returncode != status:
                raise ValueError(f'{name}: expected exit {status}, received {process.returncode}')
            report = json.loads((output / name / 'report.json').read_text())
            if report['report_schema_version'] != 4 or {f['code'] for f in report['failures']} != codes:
                raise ValueError(f'{name}: unexpected report version or failure reason')
            if report['passed'] is not (status == 0) or not report['provenance'] or not report['case_changes']:
                raise ValueError(f'{name}: incomplete evaluation evidence')
            if 'excessive_drop' in codes and real and {f['metric'] for f in report['failures']} != {
                'fact_coverage', 'citation_label_coverage', 'retrieval_recall'}:
                raise ValueError(f'{name}: unexpected regressed metrics')
            if name == 'citation-enum' and (report['citation_existence_gate']['candidate_unknown_count'] != 0
                                            or report['provenance']['code_target_validation'] != 'matched'):
                raise ValueError('citation-enum: invalid passing evidence')
            if not (output / name / 'report.md').is_file():
                raise ValueError(f'{name}: missing Markdown report')
            print(f'{name}: verified expected evaluation exit {status}', flush=True)
        if baseline_hashes() != expected:
            raise ValueError('baseline changed during replay')
        print(f'All eight replays verified; baseline unchanged. Reports: {output}')
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Replay verification failed: {error}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
