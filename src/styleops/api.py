import hmac,logging,os,uuid,json,time
from contextlib import asynccontextmanager
from fastapi import FastAPI,Depends,Header,HTTPException,Request
from fastapi.responses import FileResponse
from langsmith import tracing_context
from .pipeline import Pipeline
from .llm import ModelFailure
from .config import ROOT
from .schemas import TransformRequest
logging.basicConfig(level=logging.INFO, format="%(message)s")
@asynccontextmanager
async def lifespan(app):
    app.state.pipeline=Pipeline()
    try:
        yield
    finally:
        app.state.pipeline.llm.close()
app=FastAPI(title="Riyadh Style MLOps",version="0.3.0",lifespan=lifespan)
@app.middleware("http")
async def request_context(request:Request,call_next):
    request.state.request_id=str(uuid.uuid4());start=time.perf_counter()
    response=await call_next(request)
    response.headers["X-Request-ID"]=request.state.request_id
    logging.getLogger("styleops").info(json.dumps({"request_id":request.state.request_id,"status":response.status_code,"path":request.url.path,"duration_s":time.perf_counter()-start}))
    return response

def authorize(x_api_key:str|None=Header(default=None)):
    expected=os.getenv("APP_API_KEY","")
    if expected and not hmac.compare_digest(x_api_key or "",expected): raise HTTPException(401,"Invalid API key")
@app.get("/health")
def health(): return {"status":"ok"}
@app.get("/")
def home(): return FileResponse(ROOT / "ui/index.html")
@app.post("/transform",dependencies=[Depends(authorize)])
def transform(body:TransformRequest,request:Request):
    rid=request.state.request_id
    try:
        with tracing_context(metadata={"request_id":rid,"backend":request.app.state.pipeline.settings.backend}):
            return request.app.state.pipeline.transform(body.text,body.text_type,request_id=rid)
    except Exception as exc:
        # Never return/log raw SDK errors, prompts, secrets or submitted text.
        logging.getLogger("styleops").error(json.dumps({"request_id":rid,"error_type":type(exc).__name__,"diagnostic":str(exc) if isinstance(exc,ModelFailure) else "Use local debugger"}))
        raise HTTPException(502,detail={"message":"Pipeline failed; use request_id to investigate", "request_id":rid}) from None
