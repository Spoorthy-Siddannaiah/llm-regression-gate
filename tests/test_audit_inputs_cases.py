import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from llm_reliability.loading import InputLoadError, load_comparison, load_corpus, load_dataset, load_gate_policy
from llm_reliability.gates import GatePolicy, compare_and_gate
from llm_reliability.models import ComparisonInput
from llm_reliability.reports import render_json, render_markdown

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('body,loader', [
    ('{"SENSITIVE_KEY":"first","SENSITIVE_KEY":"second"}',load_corpus),
    ('{"cases":[{"SENSITIVE_KEY":1,"SENSITIVE_KEY":2}]}',load_dataset),
    ('{"fact_coverage":{"minimum":0,"minimum":1}}',load_gate_policy),
])
def test_duplicate_json_keys_rejected_without_echoing_keys(tmp_path,body,loader):
    p=tmp_path/'ambiguous.json';p.write_text(body)
    with pytest.raises(InputLoadError) as error: loader(p)
    assert 'duplicate JSON object key' in str(error.value)
    assert 'SENSITIVE_KEY' not in str(error.value)
    assert str(p) in str(error.value)


def test_source_labels_must_exist_but_unknown_observations_still_load(tmp_path):
    d=tmp_path/'dataset.json';s=tmp_path/'sources.json'
    d.write_bytes((ROOT/'datasets/support_policy/v1/dataset.json').read_bytes())
    s.write_text('{"refund-policy-v1":"refund", "other":"other passage"}')
    with pytest.raises(InputLoadError,match='cases.1.relevant_source_ids'):
        load_comparison(d,ROOT/'recordings/baseline.synthetic.v1.json',ROOT/'recordings/candidate.synthetic.v2.json')
    s.write_bytes((ROOT/'datasets/support_policy/v1/sources.json').read_bytes())
    candidate=json.loads((ROOT/'recordings/candidate.synthetic.v2.json').read_text())
    candidate['responses'][0]['cited_source_ids']=['unknown-observation']
    p=tmp_path/'candidate.json';p.write_text(json.dumps(candidate))
    assert load_comparison(d,ROOT/'recordings/baseline.synthetic.v1.json',p).candidate.responses[0].cited_source_ids==['unknown-observation']


def hidden_regression(critical=False):
    x=load_comparison(ROOT/'datasets/support_policy/v1/dataset.json',ROOT/'recordings/baseline.synthetic.v1.json',ROOT/'recordings/candidate.synthetic.v1.json').model_dump(mode='json')
    x['dataset']['cases'][0]['criticality']='critical' if critical else 'standard'
    x['baseline']['responses'][1]['answer']=''
    x['candidate']['responses'][0]['answer']=''
    return ComparisonInput.model_validate_json(json.dumps(x))


def test_hidden_regression_visible_without_changing_default_aggregate_gate():
    result=compare_and_gate(hidden_regression())
    assert result.passed and result.metrics[0].delta==0
    payload=json.loads(render_json(result))
    changes=payload['case_changes']
    assert [c['status'] for c in changes]==['regressed','improved']
    assert changes[0]['regressed_metrics']==['fact_coverage']
    assert changes[1]['improved_metrics']==['fact_coverage']
    assert 'regressed' in render_markdown(result)
    assert not changes[0]['critical_regression']


def test_critical_highlight_and_opt_in_case_guard():
    result=compare_and_gate(hidden_regression(critical=True))
    assert json.loads(render_json(result))['case_changes'][0]['critical_regression']
    assert not result.passed
    guarded=compare_and_gate(hidden_regression(),policy=GatePolicy(max_regressed_cases=0))
    assert [f.code for f in guarded.failures]==['excessive_case_regressions']
    assert guarded.policy.model_dump()['max_regressed_cases']==0
    assert compare_and_gate(hidden_regression(),policy=GatePolicy(max_regressed_cases=1)).passed
    assert 'max_regressed_cases' not in GatePolicy().model_dump()
    with pytest.raises(ValidationError): GatePolicy(max_regressed_cases=True)
    with pytest.raises(ValidationError): GatePolicy(max_regressed_cases=-1)


def test_optional_reference_file_uses_duplicate_key_guard(tmp_path):
    from llm_reliability.alternative_diagnostics import build_diagnostic
    references=tmp_path/'references.json'
    references.write_text('{"PRIVATE_KEY":{},"PRIVATE_KEY":{}}')
    with pytest.raises(InputLoadError,match='duplicate JSON object key') as error:
        build_diagnostic(ROOT/'datasets/squad/v1/dataset.json',ROOT/'datasets/squad/v1/sources.json',references,
                         ROOT/'recordings/squad/llama3.2-bm25-v1/recording.json',
                         ROOT/'recordings/squad/llama3.2-bm25-top1-v1/recording.json')
    assert 'PRIVATE_KEY' not in str(error.value)
