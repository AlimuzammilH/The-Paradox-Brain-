from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.orchestrator import Orchestrator

app = FastAPI()
paradox = Orchestrator()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)

@app.post("/chat")
async def chat(message: dict):
    response = paradox.route(message["text"])
    return {"response": response, "status": "processing_complete"}
