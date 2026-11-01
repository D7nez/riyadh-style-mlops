
import json
from pathlib import Path
import pytest,mlflow
from styleops.config import ROOT,Settings
from styleops.compare import compare,preflight
from styleops.llm import ModelClient,ModelFailure

def config(tmp_path):
    p=tmp_path/"config.yaml"
    p.write_text("experiment: test-provider-comparison\nrepetitions: 2\nwarmup: true\npreflight: true\ncandidates:\n  - {name: mock-a, backend: mock, model: a}\n  - {name: mock-b, backend: mock, model: b}\n")
    return p

def test_fixed_inputs_persisted_and_no_auto_winner(tmp_path,monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI","sqlite:///"+str(tmp_path/"mlflow.db"))
    result=compare(config(tmp_path),ROOT/"evaluation/cases.jsonl",tmp_path/"reports")
    assert len(result["runs"])==4
    assert result["automatic_winner"] is None
    assert all(r["success_rate"]==1 for r in result["runs"])
    out=Path(result["output_directory"])
    records=json.loads((out/"predictions.json").read_text())
    for case in {r["case_id"] for r in records}:
        assert len({r["request_sha256"] for r in records if r["case_id"]==case})==1
    assert all("estimated_cost_usd" not in r for r in result["runs"])
    assert (out/"comparison.html").exists() and (out/"human_review.csv").exists()
    assert len(records)==12 # warmup calls excluded
    run=mlflow.get_run(result["runs"][0]["run_id"])
    assert run.data.params["mode"]=="rewrite_only_fixed_context_no_repair"
    assert run.data.tags["evaluation_status"]=="passed"

def test_preflight_fails_before_benchmark_for_missing_model(monkeypatch):
    monkeypatch.setattr(ModelClient,"inventory",lambda self:[{"name":"available"}])
    with pytest.raises(ValueError,match="Model unavailable"):
        preflight({"candidates":[{"name":"bad","backend":"ollama","model":"missing"}]},Settings())

def test_comparison_failure_metrics_and_status(tmp_path,monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI","sqlite:///"+str(tmp_path/"mlflow.db"))
    def fail(*a,**kw): raise ModelFailure("ollama stage=rewrite: token limit reached")
    monkeypatch.setattr(ModelClient,"call",fail)
    result=compare(config(tmp_path),ROOT/"evaluation/cases.jsonl",tmp_path/"reports")
    assert all(r["success_rate"]==0 and r["failed_cases"]==3 for r in result["runs"])
    assert all("latency_s" not in r for r in result["runs"])
    run=mlflow.get_run(result["runs"][0]["run_id"])
    assert run.data.tags["evaluation_status"]=="failed"
