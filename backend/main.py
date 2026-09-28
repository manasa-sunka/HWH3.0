import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI
from pydantic import BaseModel
from ai_agent.agent import analyze_incident


app = FastAPI(
    title="Hindsight AI Incident Response Agent",
    description="AI-powered incident analysis system",
    version="1.0.0"
)


class Event(BaseModel):
    timestamp: str
    type: str
    message: str


class Incident(BaseModel):
    incident_id: str
    service: str
    severity: str
    events: list[Event]


@app.get("/")
def root():
    return {
        "message": "Hindsight AI Incident Response Agent is running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


@app.post("/analyze")
def analyze(incident: Incident):
    return analyze_incident(incident.model_dump())