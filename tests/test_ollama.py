
import json
from dataclasses import replace
import httpx,pytest
from styleops.config import Settings
from styleops.llm import ModelClient,ModelFailure

def ollama_client(handler,model="qwen2.5:latest"):
    settings=Settings(backend="ollama",model=model)
    client=ModelClient(settings);client.http.close()
    client.http=httpx.Client(base_url="http://test",transport=httpx.MockTransport(handler))
    return client

def test_ollama_payload_and_token_mapping():
    def handler(request):
        body=json.loads(request.content)
        assert request.url.path=="/api/chat"
        assert body["stream"] is False
        assert body["options"]["num_ctx"]==8192
        assert body["options"]["num_predict"]==1800
        assert body["format"]=="json"
        assert "think" not in body
        return httpx.Response(200,json={"done":True,"done_reason":"stop","message":{"content":"صياغة"},"prompt_eval_count":100,"eval_count":30,"load_duration":2000000000,"eval_duration":3000000000})
    client=ollama_client(handler)
    result=client.call("classify",client.settings.model,"تعليمات","نص",max_tokens=1800)
    assert result["input_tokens"]==100 and result["output_tokens"]==30
    assert result["usage_metadata"]["total_tokens"]==130
    assert result["load_duration_s"]==2
    client.close()

def test_qwen3_disables_thinking():
    def handler(request):
        assert json.loads(request.content)["think"] is False
        return httpx.Response(200,json={"done":True,"message":{"content":"نص"}})
    client=ollama_client(handler,"qwen3:8b")
    assert client.call("rewrite","qwen3:8b","system","text")["content"]=="نص"
    client.close()

@pytest.mark.parametrize("payload",[{"done":True,"message":{"content":""}},{"done":True,"done_reason":"length","message":{"content":"partial"}},{"done":False,"message":{"content":"partial"}}])
def test_incomplete_and_empty_responses_fail(payload):
    client=ollama_client(lambda r:httpx.Response(200,json=payload))
    with pytest.raises(ModelFailure): client.call("rewrite","qwen2.5:latest","s","t")
    client.close()

def test_ollama_failure_redacts_raw_error():
    client=ollama_client(lambda r:httpx.Response(500,json={"error":"sensitive-input-and-key"}))
    with pytest.raises(ModelFailure) as exc: client.call("rewrite","qwen2.5:latest","s","t")
    assert "status=500" in str(exc.value)
    assert "sensitive-input-and-key" not in str(exc.value)
    client.close()

def test_ollama_model_inventory():
    client=ollama_client(lambda r:httpx.Response(200,json={"models":[{"name":"qwen2.5:latest","digest":"abc","size":123,"details":{"quantization_level":"Q4_K_M"}}]}))
    assert client.inventory()[0]["digest"]=="abc"
    client.close()

def test_gpt_oss_budget_and_low_reasoning():
    from types import SimpleNamespace
    client=ModelClient(Settings(backend="mock"));client.settings=replace(client.settings,backend="groq")
    def create(**kwargs):
        assert kwargs["max_completion_tokens"]==4096
        assert kwargs["reasoning_effort"]=="low"
        assert kwargs["include_reasoning"] is False
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="{}"),finish_reason="stop")],usage=None)
    client.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    assert client.call("classify","openai/gpt-oss-20b","s","t",max_tokens=200)["content"]=="{}"
