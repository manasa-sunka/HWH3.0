import json
import sys
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, AliasChoices, ConfigDict

from ai_agent.agent import analyze_incident, load_incident
from backend.database import init_db, save_incident, list_incidents, get_incident, delete_incident


# Initialize Database on launch
init_db()

app = FastAPI(
    title="Hindsight AI Incident Response Agent",
    description="AI-powered incident analysis system with persistent database & visual dashboard",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files for Frontend
FRONTEND_DIR = PROJECT_ROOT / "frontend"
app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")


class Event(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "timestamp": "10:01",
                "type": "metric",
                "message": "CPU usage increased to 92%"
            }
        }
    )

    timestamp: str = Field(
        ...,
        validation_alias=AliasChoices("timestamp", "time", "ts"),
        description="Time when the event occurred",
        examples=["10:01", "2026-09-29T10:01:00Z"]
    )
    type: str = Field(
        ...,
        validation_alias=AliasChoices("type", "event_type", "category"),
        description="Type of the event (e.g., metric, error, alert, log)",
        examples=["metric", "error", "alert"]
    )
    message: str = Field(
        ...,
        validation_alias=AliasChoices("message", "msg", "description", "log"),
        description="Detailed event message or log description",
        examples=["CPU usage increased to 92%", "Database connection pool exhausted"]
    )


class Incident(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        json_schema_extra={
            "example": {
                "incident_id": "INC-001",
                "service": "Payment API",
                "severity": "HIGH",
                "events": [
                    {
                        "timestamp": "10:01",
                        "type": "metric",
                        "message": "CPU usage increased to 92%"
                    },
                    {
                        "timestamp": "10:02",
                        "type": "metric",
                        "message": "API latency increased to 4.8 seconds"
                    },
                    {
                        "timestamp": "10:03",
                        "type": "error",
                        "message": "Database connection pool exhausted"
                    },
                    {
                        "timestamp": "10:04",
                        "type": "error",
                        "message": "Payment API requests failing with HTTP 503"
                    },
                    {
                        "timestamp": "10:05",
                        "type": "alert",
                        "message": "Payment API availability below threshold"
                    }
                ]
            }
        }
    )

    incident_id: str = Field(
        ...,
        validation_alias=AliasChoices("incident_id", "id", "indicent_id"),
        description="Unique identifier for the incident",
        examples=["INC-001", "INC-2026-009"]
    )
    service: str = Field(
        ...,
        validation_alias=AliasChoices("service", "services", "service_name"),
        description="Name of the affected service",
        examples=["Payment API", "Auth Service", "Checkout Service"]
    )
    severity: str = Field(
        ...,
        validation_alias=AliasChoices("severity", "level", "priority"),
        description="Incident severity level",
        examples=["HIGH", "MEDIUM", "LOW", "CRITICAL"]
    )
    events: List[Event] = Field(
        ...,
        validation_alias=AliasChoices("events", "logs", "event_list"),
        description="List of events/logs associated with the incident"
    )


# Serve Frontend Web Dashboard
@app.get("/")
def serve_dashboard():
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {
        "message": "Hindsight AI Incident Response Agent is running",
        "docs": "/docs"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "database": "sqlite",
        "model": "gemini-3.8-flash"
    }


# Sample Incident Data
@app.get("/api/sample")
def get_sample_data():
    try:
        return load_incident()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Database CRUD endpoints
@app.get("/api/incidents")
def list_saved_incidents(limit: int = 50):
    return list_incidents(limit=limit)


@app.get("/api/incidents/{incident_id}")
def get_saved_incident(incident_id: str):
    data = get_incident(incident_id)
    if not data:
        raise HTTPException(status_code=404, detail="Incident not found")
    return data


@app.delete("/api/incidents/{incident_id}")
def delete_saved_incident(incident_id: str):
    success = delete_incident(incident_id)
    if not success:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"deleted": True, "incident_id": incident_id}


# AI Analysis and Persistence
@app.post("/analyze")
@app.post("/api/analyze")
def analyze(incident: Incident):
    try:
        input_data = incident.model_dump()
        analysis_result = analyze_incident(input_data)
        
        # Save to SQLite Database
        save_incident(input_data, analysis_result)
        
        return analysis_result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))