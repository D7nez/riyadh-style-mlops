import argparse,json
from .config import ROOT

def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest="command",required=True)
    run=sub.add_parser("transform");run.add_argument("text");run.add_argument("--type",default="مقال")
    evaluation=sub.add_parser("benchmark");evaluation.add_argument("--config",default=str(ROOT/"configs/benchmark.yaml"));evaluation.add_argument("--cases",default=str(ROOT/"evaluation/cases.jsonl"));evaluation.add_argument("--output",default=str(ROOT/"reports"))
    comparison=sub.add_parser("compare");comparison.add_argument("--config",default=str(ROOT/"configs/compare.yaml"));comparison.add_argument("--cases",default=str(ROOT/"evaluation/cases.jsonl"));comparison.add_argument("--output",default=str(ROOT/"reports"))
    doctor=sub.add_parser("doctor");doctor.add_argument("--config",default=str(ROOT/"configs/compare.yaml"))
    args=parser.parse_args()
    if args.command=="transform":
        from .pipeline import Pipeline
        result=Pipeline().transform(args.text,args.type)
    elif args.command=="doctor":
        from .compare import preflight,read_spec
        from .config import Settings
        result=preflight(read_spec(args.config),Settings())
    elif args.command=="compare":
        from .compare import compare
        result=compare(args.config,args.cases,args.output)
    else:
        from .evaluate import benchmark
        result=benchmark(args.config,args.cases,args.output)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    import os
    if os.getenv("LANGSMITH_TRACING","").lower()=="true":
        from langsmith import Client
        Client().flush()
if __name__=="__main__": main()
