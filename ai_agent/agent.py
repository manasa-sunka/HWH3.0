import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# Project location
project_root = Path(__file__).resolve().parent.parent

# Load Gemini API key
load_dotenv(project_root / "backend" / ".env")

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


def load_incident():
    incident_file = project_root / "data" / "incident.json"

    with open(incident_file, "r", encoding="utf-8") as file:
        return json.load(file)


def analyze_with_ai(incident):

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
  "incident_id": "...",
  "service": "...",
  "severity": "...",
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

    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=prompt
    )

    text = response.text

    # Remove markdown code fences if Gemini adds them
    text = text.replace("```json", "").replace("```", "").strip()

    return json.loads(text)


def analyze_incident(incident):
    return analyze_with_ai(incident)


def run_analysis():
    incident = load_incident()
    return analyze_incident(incident)


if __name__ == "__main__":
    result = run_analysis()
    print(json.dumps(result, indent=2))