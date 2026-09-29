import json
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


# ============================================================
# PROJECT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from backend/.env
load_dotenv(PROJECT_ROOT / "backend" / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not configured in backend/.env"
    )

# Create Gemini client
client = genai.Client(api_key=GEMINI_API_KEY)


# ============================================================
# LOAD INCIDENT FROM JSON FILE
# ============================================================

def load_incident():
    incident_file = PROJECT_ROOT / "data" / "incident.json"

    if not incident_file.exists():
        raise FileNotFoundError(
            f"Incident file not found: {incident_file}"
        )

    with open(incident_file, "r", encoding="utf-8") as file:
        return json.load(file)


# ============================================================
# CLEAN GEMINI RESPONSE
# ============================================================

def clean_json_response(text):
    """
    Removes markdown code fences if Gemini returns JSON
    inside ```json ... ``` blocks.
    """

    if not text:
        raise RuntimeError(
            "Gemini returned an empty response."
        )

    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json"):]

    elif text.startswith("```"):
        text = text[len("```"):]

    if text.endswith("```"):
        text = text[:-3]

    return text.strip()


# ============================================================
# AI INCIDENT ANALYSIS
# ============================================================

def analyze_with_ai(incident):

    prompt = f"""
You are Hindsight, an AI Incident Response Investigator.

Your job is to analyze a software incident using ONLY the
evidence provided in the incident data.

IMPORTANT RULES:

1. Do not invent facts.
2. Analyze events chronologically.
3. Separate direct evidence from inference.
4. Treat the root cause as a hypothesis unless directly proven.
5. Explain why the suspected root cause is supported.
6. Identify missing information and uncertainty.
7. Recommend practical next actions.
8. Do not create evidence that does not exist.
9. If the evidence is insufficient, clearly say so.
10. Keep the analysis concise and useful for an incident responder.

Return ONLY valid JSON.

Use EXACTLY this structure:

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

INCIDENT DATA:

{json.dumps(incident, indent=2)}
"""

    # ========================================================
    # GEMINI MODEL FALLBACKS
    # ========================================================

    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash",
        "gemini-3.5-flash-lite"
    ]

    last_error = None

    for model in models_to_try:

        try:
            print(f"Trying Gemini model: {model}")

            response = client.models.generate_content(
                model=model,
                contents=prompt
            )

            if not response or not response.text:
                raise RuntimeError(
                    f"{model} returned an empty response."
                )

            print(f"Gemini model succeeded: {model}")

            return parse_ai_response(response.text)

        except Exception as error:

            print(
                f"Gemini model failed: "
                f"{model} -> {type(error).__name__}: {error}"
            )

            last_error = error

    # ========================================================
    # ALL MODELS FAILED
    # ========================================================

    raise RuntimeError(
        f"All Gemini models failed. Last error: {last_error}"
    )


# ============================================================
# PARSE GEMINI JSON
# ============================================================

def parse_ai_response(text):

    cleaned_text = clean_json_response(text)

    try:
        result = json.loads(cleaned_text)

    except json.JSONDecodeError as error:

        raise RuntimeError(
            "Gemini returned invalid JSON. "
            f"JSON parsing error: {error}. "
            f"Raw response: {cleaned_text}"
        )

    # Basic validation
    required_fields = [
        "incident_id",
        "service",
        "severity",
        "timeline",
        "observations",
        "root_cause",
        "confidence",
        "evidence",
        "recommended_actions",
        "uncertainty"
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in result
    ]

    if missing_fields:
        raise RuntimeError(
            "Gemini response is missing required fields: "
            + ", ".join(missing_fields)
        )

    return result


# ============================================================
# MAIN ANALYSIS FUNCTION
# ============================================================

def analyze_incident(incident):

    if not incident:
        raise ValueError(
            "Incident data cannot be empty."
        )

    return analyze_with_ai(incident)


# ============================================================
# LOCAL TEST
# ============================================================

def run_analysis():

    incident = load_incident()

    result = analyze_incident(incident)

    return result


# ============================================================
# RUN DIRECTLY
# ============================================================

if __name__ == "__main__":

    result = run_analysis()

    print(
        json.dumps(
            result,
            indent=2,
            ensure_ascii=False
        )
    )