import json
from dataclasses import replace
import pytest
from fastapi.testclient import TestClient
from styleops.config import Settings
from styleops.pipeline import Pipeline
from styleops.review import style_issues, factual_metrics
from styleops.retrieval import boolean
from styleops.api import app

@pytest.fixture
def settings(): return Settings(backend="mock",retrieval="tfidf")

def test_mock_path(settings):
    result=Pipeline(settings).transform("تم افتتاح 12 حديقة.")
    assert result["output"]=="تم افتتاح 12 حديقة."
    assert result["metrics"]["number_recall"]==1
    assert len(result["examples"])==3
    assert result["backend"]=="mock"

def test_retrieval_exclusion(settings):
    pipe=Pipeline(settings)
    result=pipe.transform("تطوير الحدائق",exclude_ids={row["id"] for row in pipe.retriever.rows})
    assert not result["examples"]

@pytest.mark.parametrize("value,expected",[("False",False),("0",False),("True",True),("1",True),("",False)])
def test_csv_booleans(value,expected): assert boolean(value)==expected

def test_arabic_numbers():
    assert factual_metrics("تطوير ١٢ حديقة", "تطوير 12 حديقة")=={"number_recall":1,"new_number_count":0}
    assert factual_metrics("12 حديقة", "13 حديقة")["number_recall"]==0

def test_review():
    assert "latin_characters" in style_issues("AI")
    assert "repeated_hayth" in style_issues("حيث نعمل حيث ننجز")
    assert not style_issues("حيث نعمل\n\nحيث ننجز")

class InvalidMeta:
    def call(self,stage,model,system,text,*args):
        return {"content":"bad json" if stage=="classify" else text,"input_tokens":1,"output_tokens":1}
def test_bad_metadata_fallback(settings):
    result=Pipeline(settings,llm=InvalidMeta()).transform("نطور المدينة")
    assert "metadata_invalid_using_semantic_only" in result["warnings"]

class BadRepair:
    def call(self,stage,model,system,text,*args):
        return {"content":json.dumps({}) if stage=="classify" else "AI", "input_tokens":1,"output_tokens":1}
def test_repair_is_rechecked(settings):
    result=Pipeline(settings,llm=BadRepair()).transform("نطور المدينة")
    assert result["review_required"]
    assert "latin_characters" in result["final_issues"]
    assert result["metrics"]["input_tokens"]==4

def test_whitespace(settings):
    with pytest.raises(ValueError): Pipeline(settings).transform("   ")

def test_provider_needs_key(monkeypatch,settings):
    monkeypatch.delenv("GROQ_API_KEY",raising=False)
    with pytest.raises(ValueError): replace(settings,backend="groq").validate()

def test_api(monkeypatch):
    monkeypatch.setenv("APP_API_KEY","test-secret")
    with TestClient(app) as client:
        assert client.get("/health").status_code==200
        assert client.get("/").status_code==200
        assert client.post("/transform",json={"text":"نطور المدينة"}).status_code==401
        assert client.post("/transform",headers={"X-API-Key":"test-secret"},json={"text":" "}).status_code==422
        response=client.post("/transform",headers={"X-API-Key":"test-secret"},json={"text":"نطور المدينة"})
        assert response.status_code==200
        assert response.json()["request_id"]==response.headers["X-Request-ID"]

def test_error_does_not_leak(monkeypatch):
    with TestClient(app) as client:
        def fail(*a,**k): raise RuntimeError("sensitive-provider-secret")
        monkeypatch.setattr(app.state.pipeline,"transform",fail)
        response=client.post("/transform",json={"text":"نطور المدينة"})
        assert response.status_code==502
        assert "sensitive-provider-secret" not in response.text

def test_groq_request_and_usage(settings,monkeypatch):
    import httpx
    from groq import Groq
    from styleops.llm import ModelClient
    monkeypatch.setenv("GROQ_API_KEY","test-placeholder")
    def respond(request):
        payload=json.loads(request.content)
        assert payload["model"]=="fixture-model"
        assert payload["messages"][1]["content"]=="نص تجريبي"
        return httpx.Response(200,json={"id":"fixture","object":"chat.completion","created":0,"model":"fixture-model","choices":[{"index":0,"message":{"role":"assistant","content":"صياغة تجريبية"},"finish_reason":"stop"}],"usage":{"prompt_tokens":10,"completion_tokens":4,"total_tokens":14}})
    # Instantiate provider with SDK transport injection; no external network call.
    llm=ModelClient(settings)
    llm.settings=replace(settings,backend="groq")
    llm.client=Groq(api_key="test-placeholder",http_client=httpx.Client(transport=httpx.MockTransport(respond)))
    result=llm.call("rewrite","fixture-model","تعليمات","نص تجريبي")
    assert result["content"]=="صياغة تجريبية"
    assert result["input_tokens"]==10
    assert result["usage_metadata"]["total_tokens"]==14
