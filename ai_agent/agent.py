import json
from pathlib import Path


def load_incident():
    project_root = Path(__file__).resolve().parent.parent
    incident_file = project_root / "data" / "incident.json"

    with open(incident_file, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_incident(incident):
    events = incident["events"]

    timeline = []

    for event in events:
        timeline.append({
            "time": event["timestamp"],
            "type": event["type"],
            "message": event["message"]
        })

    database_issue = any(
        "connection pool exhausted" in event["message"].lower()
        for event in events
    )

    payment_failure = any(
        "503" in event["message"]
        for event in events
    )

    if database_issue and payment_failure:
        root_cause = (
            "Database connection pool exhaustion is the likely root cause "
            "of the Payment API failures."
        )
        confidence = "HIGH"
    else:
        root_cause = "Root cause could not be determined."
        confidence = "LOW"

    return {
        "incident_id": incident["incident_id"],
        "service": incident["service"],
        "severity": incident["severity"],
        "timeline": timeline,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence": [
            "Database connection pool exhausted",
            "Payment API requests failing with HTTP 503"
        ]
    }


def run_analysis():
    incident = load_incident()
    return analyze_incident(incident)


if __name__ == "__main__":
    result = run_analysis()
    print(json.dumps(result, indent=2))