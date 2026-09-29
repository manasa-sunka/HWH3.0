import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import errors


# Project location
project_root = Path(__file__).resolve().parent.parent

# Load Gemini API key from backend/.env if present
load_dotenv(project_root / "backend" / ".env")

# Priority list of models with automatic fallbacks
MODELS = [
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-flash-latest"
]


def get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_gemini_api_key_here":
        raise ValueError(
            "GEMINI_API_KEY is not set. Please set your GEMINI_API_KEY in backend/.env"
        )
    return genai.Client(api_key=api_key)


def load_incident():
    incident_file = project_root / "data" / "incident.json"

    with open(incident_file, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_with_ai(incident):
    client = get_gemini_client()

    prompt = f"""
You are Hindsight, an AI incident response investigator.

Analyze the software incident using ONLY the evidence provided.

Rules:
1. Do not invent facts.
2. Analyze events chronologically.
3. Separate evidence from inference.
4. Treat root cause as a hypothesis unless directly proven.
5. Explain why the root cause is suspected.
6. Identify uncertainty.
7. Recommend practical next actions.

Return ONLY valid JSON in this format:

{{
  "incident_id": "{incident.get('incident_id', 'INC-001')}",
  "service": "{incident.get('service', 'Service')}",
  "severity": "{incident.get('severity', 'HIGH')}",
  "timeline": [],
  "observations": [],
  "root_cause": "...",
  "confidence": "HIGH/MEDIUM/LOW",
  "evidence": [],
  "recommended_actions": [],
  "uncertainty": []
}}

Incident:

{json.dumps(incident, indent=2)}
"""

    last_error = None

    for model_name in MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )

            text = response.text
            if not text:
                continue

            # Remove markdown code fences if model adds them
            text = text.replace("```json", "").replace("```", "").strip()

            result = json.loads(text)
            
            # Ensure key fields exist
            result.setdefault("incident_id", incident.get("incident_id", "INC-001"))
            result.setdefault("service", incident.get("service", "Service"))
            result.setdefault("severity", incident.get("severity", "HIGH"))
            result.setdefault("model_used", model_name)

            return result

        except (errors.APIError, errors.ClientError, Exception) as e:
            last_error = e
            # Try next model in candidate list
            continue

    raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")


def analyze_incident(incident):
    return analyze_with_ai(incident)


def run_analysis():
    incident = load_incident()
    return analyze_incident(incident)


if __name__ == "__main__":
    result = run_analysis()
    print(json.dumps(result, indent=2))