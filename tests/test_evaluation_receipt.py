import hashlib
import json
from pathlib import Path

import pytest

from llm_reliability.cli import main
from llm_reliability.evaluation_receipt import EvaluationReceipt, evaluator_hashes
from llm_reliability.loading import load_comparison
from llm_reliability.gates import compare_and_gate
from llm_reliability.reports import render_json

ROOT=Path(__file__).resolve().parents[1]


def args(output,dataset=None):
    return ['--dataset',str(dataset or ROOT/'datasets/support_policy/v1/dataset.json'),
            '--baseline',str(ROOT/'recordings/baseline.synthetic.v1.json'),
            '--candidate',str(ROOT/'recordings/candidate.synthetic.v1.json'),'--output-dir',str(output)]


def test_cli_receipt_reproducible_and_contains_hashes_not_payloads(tmp_path):
    assert main(args(tmp_path/'one'))==0
    assert main(args(tmp_path/'two'))==0
    first=json.loads((tmp_path/'one/report.json').read_text())
    assert (tmp_path/'one/report.json').read_bytes()==(tmp_path/'two/report.json').read_bytes()
    receipt=first['provenance']
    for name,path in [('dataset','datasets/support_policy/v1/dataset.json'),('corpus','datasets/support_policy/v1/sources.json'),('baseline','recordings/baseline.synthetic.v1.json'),('candidate','recordings/candidate.synthetic.v1.json')]:
        assert receipt['input_sha256'][name]==hashlib.sha256((ROOT/path).read_bytes()).hexdigest()
    assert receipt['evaluator_source_sha256']==evaluator_hashes()
    assert receipt['code_target_validation']=='not_requested'
    assert 'proof of purchase' not in json.dumps(receipt)
    assert 'Acorn' not in json.dumps(receipt)
    assert 'Evaluation provenance receipt' in (tmp_path/'one/report.md').read_text()


def test_input_drift_before_report_returns_two(tmp_path,monkeypatch):
    from llm_reliability.cli import compare_and_gate as original
    dataset=tmp_path/'dataset.json';dataset.write_bytes((ROOT/'datasets/support_policy/v1/dataset.json').read_bytes())
    def change(*a,**kw):
        result=original(*a,**kw);dataset.write_bytes(dataset.read_bytes()+b'\n');return result
    monkeypatch.setattr('llm_reliability.cli.compare_and_gate',change)
    assert main(args(tmp_path/'out',dataset))==2
    assert not (tmp_path/'out').exists()


def test_api_explicitly_marks_missing_receipt_and_rejects_mismatched_versions():
    gate=compare_and_gate(load_comparison(ROOT/'datasets/support_policy/v1/dataset.json',ROOT/'recordings/baseline.synthetic.v1.json',ROOT/'recordings/candidate.synthetic.v1.json'))
    assert json.loads(render_json(gate))['provenance'] is None
    receipt=EvaluationReceipt(input_sha256={name:'0'*64 for name in ('dataset','baseline','candidate')},evaluator_source_sha256=evaluator_hashes(),evaluator_version='wrong',policy_version=gate.policy.policy_version,code_target_validation='not_requested')
    with pytest.raises(ValueError,match='versions'):render_json(gate,provenance=receipt)
