from pydantic import BaseModel, Field
from typing import List


class Event(BaseModel):
    timestamp: str = Field(
        ...,
        examples=["2026-09-28T22:30:15Z"]
    )
    type: str = Field(
        ...,
        examples=["ERROR"]
    )
    message: str = Field(
        ...,
        examples=["Database connection timeout"]
    )


class IncidentRequest(BaseModel):
    incident_id: str = Field(
        ...,
        examples=["INC-2026-001"]
    )
    service: str = Field(
        ...,
        examples=["payment-service"]
    )
    severity: str = Field(
        ...,
        examples=["HIGH"]
    )
    events: List[Event]