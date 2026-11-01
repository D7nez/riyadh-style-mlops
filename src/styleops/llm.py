import json, os, time
import httpx
from langsmith import traceable

class ModelFailure(RuntimeError):
    """Sanitized diagnostics: no submitted text, credentials or raw SDK errors."""

class ModelClient:
    def __init__(self, settings):
        self.settings=settings
        self.http=None
        if settings.backend=="groq":
            from groq import Groq
            self.client=Groq(api_key=os.environ["GROQ_API_KEY"],timeout=60.0,max_retries=2)
        elif settings.backend=="ollama":
            self.http=httpx.Client(base_url=settings.ollama_url.rstrip("/"),timeout=httpx.Timeout(settings.ollama_timeout,connect=10),trust_env=False)

    def inventory(self):
        if self.settings.backend=="mock": return []
        if self.settings.backend=="groq":
            return [{"name":m.id} for m in self.client.models.list().data]
        response=self.http.get("/api/tags");response.raise_for_status()
        return [{"name":m.get("name",m.get("model")),"digest":m.get("digest"),"size_bytes":m.get("size"),"details":m.get("details",{})} for m in response.json()["models"]]

    def call(self,stage,model,system,text,temperature=0,max_tokens=1500):
        backend=self.settings.backend
        messages=[{"role":"system","content":system},{"role":"user","content":text}]
        result=self._invoke(messages=messages,model=model,stage=stage,temperature=temperature,max_tokens=max_tokens,
            langsmith_extra={"name":stage,"metadata":{"ls_provider":backend,"ls_model_name":model,"stage":stage,"backend":backend,"ls_model_type":"chat","temperature":temperature}})
        return {"content":result["choices"][0]["message"]["content"],"input_tokens":result["usage_metadata"]["input_tokens"],"output_tokens":result["usage_metadata"]["output_tokens"],"usage_metadata":result["usage_metadata"],"model":model if backend!="mock" else "mock","stage":stage,"backend":backend,"duration_s":result["duration_s"],"load_duration_s":result["load_duration_s"],"generation_duration_s":result["generation_duration_s"]}

    @traceable(name="model_call",run_type="llm")
    def _invoke(self,messages,model,stage,temperature,max_tokens):
        started=time.perf_counter();backend=self.settings.backend
        load=0.0;generation=0.0
        if backend=="mock":
            content=json.dumps({"topic":None,"has_stats":False,"has_religious":False,"desired_opening":0}) if stage=="classify" else messages[-1]["content"]
            input_tokens=output_tokens=total_tokens=0
        elif backend=="groq":
            is_oss=model in {"openai/gpt-oss-20b","openai/gpt-oss-120b"}
            options={"reasoning_effort":"low","include_reasoning":False} if is_oss else {}
            try:
                r=self.client.chat.completions.create(model=model,messages=messages,temperature=temperature,max_completion_tokens=max(max_tokens,4096) if is_oss else max_tokens,**options)
            except Exception as exc:
                status=getattr(exc,"status_code",None)
                raise ModelFailure(f"groq stage={stage} model={model} error={type(exc).__name__} status={status}") from None
            if not r.choices: raise ModelFailure(f"groq stage={stage}: no choices")
            choice=r.choices[0];content=choice.message.content
            if choice.finish_reason=="length": raise ModelFailure(f"groq stage={stage}: token limit reached")
            if not content or not content.strip(): raise ModelFailure(f"groq stage={stage}: empty content finish_reason={choice.finish_reason}")
            input_tokens=r.usage.prompt_tokens if r.usage else 0
            output_tokens=r.usage.completion_tokens if r.usage else 0
            total_tokens=r.usage.total_tokens if r.usage else 0
        else:
            body={"model":model,"messages":messages,"stream":False,"keep_alive":"10m","options":{"temperature":temperature,"num_ctx":self.settings.ollama_context,"num_predict":max_tokens}}
            # Only Qwen3 opts out of thinking; do not send unsupported flags to other families.
            if model.startswith("qwen3:"): body["think"]=False
            if stage=="classify": body["format"]="json"
            try:
                response=self.http.post("/api/chat",json=body);response.raise_for_status();r=response.json()
            except Exception as exc:
                status=exc.response.status_code if isinstance(exc,httpx.HTTPStatusError) else None
                raise ModelFailure(f"ollama stage={stage} model={model} error={type(exc).__name__} status={status}") from None
            content=r.get("message",{}).get("content","")
            if r.get("done") is not True: raise ModelFailure(f"ollama stage={stage}: incomplete response")
            if r.get("done_reason")=="length": raise ModelFailure(f"ollama stage={stage}: token limit reached")
            if not content.strip(): raise ModelFailure(f"ollama stage={stage}: empty content")
            input_tokens=int(r.get("prompt_eval_count",0));output_tokens=int(r.get("eval_count",0));total_tokens=input_tokens+output_tokens
            load=r.get("load_duration",0)/1e9;generation=r.get("eval_duration",0)/1e9
        content=content.strip()
        return {"choices":[{"message":{"role":"assistant","content":content}}],"model":model,"usage_metadata":{"input_tokens":input_tokens,"output_tokens":output_tokens,"total_tokens":total_tokens},"duration_s":time.perf_counter()-started,"load_duration_s":load,"generation_duration_s":generation}

    def runtime(self):
        if self.settings.backend!="ollama": return {"status":"not_local"}
        try:
            response=self.http.get("/api/ps");response.raise_for_status()
            return {"status":"ok","models":response.json().get("models",[])}
        except Exception as exc:
            return {"status":"unavailable","error_type":type(exc).__name__}

    def close(self):
        if self.http is not None: self.http.close()
        client=getattr(self,"client",None)
        if client is not None and hasattr(client,"close"): client.close()
