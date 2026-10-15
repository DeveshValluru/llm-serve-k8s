import os, time
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoModelForCausalLM, AutoTokenizer

MODEL = os.getenv("MODEL_ID", "HuggingFaceTB/SmolLM2-135M-Instruct")
app = FastAPI()
state = {"ready": False}

class Req(BaseModel):
    prompt: str
    max_new_tokens: int = 64

@app.on_event("startup")
def load():
    state["tok"] = AutoTokenizer.from_pretrained(MODEL)
    state["model"] = AutoModelForCausalLM.from_pretrained(MODEL)
    state["ready"] = True

@app.get("/healthz")
def healthz():
    return {"status": "alive"}

@app.get("/ready")
def ready():
    if not state["ready"]:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="loading")
    return {"status": "ready"}

@app.post("/generate")
def generate(r: Req):
    t0 = time.time()
    ids = state["tok"](r.prompt, return_tensors="pt")
    out = state["model"].generate(**ids, max_new_tokens=r.max_new_tokens)
    text = state["tok"].decode(out[0], skip_special_tokens=True)
    return {"text": text, "seconds": round(time.time() - t0, 2)}