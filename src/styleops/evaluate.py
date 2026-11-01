import csv,hashlib,json,os,platform,random,subprocess,time
from dataclasses import replace
from pathlib import Path
import mlflow,yaml
from langsmith import tracing_context
from .config import ROOT,Settings
from .pipeline import Pipeline

def benchmark(config,cases,output):
    settings=Settings().validate();config=Path(config);cases=Path(cases);out=Path(output);out.mkdir(parents=True,exist_ok=True)
    spec=yaml.safe_load(config.read_text());inputs=[json.loads(line) for line in cases.read_text().splitlines() if line.strip()]
    if not inputs or not spec.get("models"): raise ValueError("Need models and cases")
    mlflow.set_tracking_uri(os.getenv("MLFLOW_TRACKING_URI","sqlite:///" + str(ROOT/"mlflow.db")))
    mlflow.set_experiment("riyadh-style-"+settings.backend)
    try: commit=subprocess.check_output(["git","rev-parse","HEAD"],stderr=subprocess.DEVNULL,text=True).strip()
    except (OSError,subprocess.CalledProcessError): commit="unversioned"
    results=[]; pipelines={}
    for model in spec["models"]:
        pipelines[model]=Pipeline(replace(settings,model=model,temperature=float(spec.get("temperature",0.6))))
    jobs=[(m,r) for m in spec["models"] for r in range(int(spec.get("repetitions",1)))];random.Random(42).shuffle(jobs)
    for model,rep in jobs:
        pipeline=pipelines[model]; records=[];success=[]
        with mlflow.start_run(run_name=f"{settings.backend}-{model}-{rep}") as run:
            params={"model":model,"analysis_model":settings.analysis_model,"backend":settings.backend,"retrieval":settings.retrieval,"top_k":settings.top_k,"embedding_model":settings.embedding_model,"temperature":pipeline.settings.temperature,"repeat":rep,"data_sha256":pipeline.retriever.data_hash,"prompt_sha256":pipeline.prompt_hash,"cases_sha256":hashlib.sha256(cases.read_bytes()).hexdigest(),"git_commit":commit,"python":platform.python_version()}
            mlflow.log_params(params);mlflow.log_artifact(str(config),"config");mlflow.log_artifact(str(cases),"evaluation")
            mlflow.log_artifact(settings.prompt,"prompts")
            rates=json.loads(os.getenv("MODEL_PRICES_JSON","{}"))
            for case in inputs:
                start=time.perf_counter()
                try:
                    with tracing_context(metadata={"mlflow_run_id":run.info.run_id,"case_id":case["id"],"repeat":rep,"model":model}):
                        result=pipeline.transform(case["text"],case.get("text_type","مقال"),exclude_ids=set(case.get("exclude_ids",[])))
                    if all(call["model"] in rates for call in result["usage"]):
                        result["metrics"]["estimated_cost_usd"]=sum((c["input_tokens"]*rates[c["model"]]["input"]+c["output_tokens"]*rates[c["model"]]["output"])/1_000_000 for c in result["usage"])
                    success.append(result);records.append({"case_id":case["id"],"status":"ok",**result})
                except Exception as exc:
                    records.append({"case_id":case["id"],"status":"error","error_type":type(exc).__name__,"latency_s":time.perf_counter()-start})
            metrics={"success_rate":len(success)/len(inputs),"failed_cases":len(inputs)-len(success)}
            if success:
                for key in set.intersection(*(set(r["metrics"]) for r in success)): metrics[key]=sum(r["metrics"][key] for r in success)/len(success)
                metrics["style_pass_rate"]=sum(not r["final_issues"] for r in success)/len(success)
            mlflow.log_metrics(metrics);mlflow.log_dict({"records":records},"results/predictions.json")
            results.append({"run_id":run.info.run_id,"model":model,"backend":settings.backend,"repeat":rep,**metrics})
    fields=list(dict.fromkeys(k for r in results for k in r))
    with (out/"comparison.csv").open("w",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(results)
    (out/"comparison.json").write_text(json.dumps(results,ensure_ascii=False,indent=2))
    return results
