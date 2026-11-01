import json
from pathlib import Path
from styleops.evaluate import benchmark
from styleops.config import ROOT

def test_benchmark_records_real_metrics(tmp_path,monkeypatch):
    monkeypatch.setenv("MLFLOW_TRACKING_URI","sqlite:///"+str(tmp_path/"mlflow.db"))
    config=tmp_path/"config.yaml";config.write_text("models: [mock-a, mock-b]\nrepetitions: 1\n")
    result=benchmark(config,ROOT/"evaluation/cases.jsonl",tmp_path/"reports")
    assert len(result)==2
    assert all(r["backend"]=="mock" and r["success_rate"]==1 for r in result)
    assert all(r["input_tokens"]==0 for r in result)
    assert (tmp_path/"reports/comparison.csv").is_file()
    assert len(json.loads((tmp_path/"reports/comparison.json").read_text()))==2

def test_all_failed_cases_are_reported(tmp_path,monkeypatch):
    from styleops.pipeline import Pipeline
    monkeypatch.setenv("MLFLOW_TRACKING_URI","sqlite:///"+str(tmp_path/"failed.db"))
    def fail(*args,**kwargs): raise TimeoutError("private provider message")
    monkeypatch.setattr(Pipeline,"transform",fail)
    config=tmp_path/"config.yaml";config.write_text("models: [mock-a]\nrepetitions: 1\n")
    result=benchmark(config,ROOT/"evaluation/cases.jsonl",tmp_path/"reports")
    assert result[0]["success_rate"]==0
    assert result[0]["failed_cases"]==3
    assert "number_recall" not in result[0]
