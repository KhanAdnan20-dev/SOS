"""
AI Classification Engine (Firebase -> Kaggle GPU Bridge)
---------------------------------------------------------
Routes transcripts through Firebase Realtime DB to a Kaggle
notebook running Qwen-2.5-7B-Instruct.

Flow:
  1. Write transcript + status=REQUESTED to Firebase pipeline.json
  2. Kaggle notebook picks it up, runs Qwen inference, writes back
     status=COMPLETED + response_json
  3. This module polls until COMPLETED, then maps Kaggle's output
     schema to the fields the dispatch service expects.

Falls back to keyword matching if Firebase is unreachable or
the polling times out.
"""

import json
import time
import requests

from config import FIREBASE_URL, AI_POLLING_TIMEOUT

# ─── Trauma Type -> Hospital specialty_tags mapping ─────────────
# Maps your AI model's trauma_type output to the hospital DB tags
TRAUMA_TO_SPECIALTY = {
    "Cardiac":        "cardiac",
    "Penetrating":    "trauma",
    "Respiratory":    "respiratory",
    "Hemorrhage":     "trauma",
    "Neurological":   "stroke",
    "Toxicology":     "poisoning",
    "Blunt_Trauma":   "trauma",
    "Anaphylaxis":    "respiratory",
    "Environmental":  "burn",
    "Unknown":        "general",
    "General":        "general",
    "Default":        "general",
}

# ─── Kaggle severity_level (1/2/3) -> dispatch urgency & label ──
SEVERITY_LEVEL_MAP = {
    1: {"severity": "Critical", "urgency_tier": "CRITICAL", "priority": 1},
    2: {"severity": "High",     "urgency_tier": "HIGH",     "priority": 2},
    3: {"severity": "Medium",   "urgency_tier": "MEDIUM",   "priority": 3},
}

# ─── Severity string -> Urgency tier mapping ────────────────────
SEVERITY_TO_URGENCY = {
    "Critical": "CRITICAL",
    "High":     "HIGH",
    "Medium":   "MEDIUM",
    "Low":      "LOW",
    "Unknown":  "MEDIUM",
}


def _firebase_pipeline_url():
    """Build the Firebase pipeline.json REST URL."""
    base = FIREBASE_URL.rstrip("/")
    return f"{base}/pipeline.json"


def _submit_to_firebase(transcript: str) -> bool:
    """Write the transcript to Firebase and mark status=REQUESTED."""
    payload = {
        "transcript": transcript,
        "status": "REQUESTED",
        "response_json": "",
    }
    try:
        resp = requests.put(_firebase_pipeline_url(), json=payload, timeout=10)
        resp.raise_for_status()
        print(f"[classifier] Transcript submitted to Firebase (status=REQUESTED)")
        return True
    except requests.RequestException as e:
        print(f"[classifier] [WARN] Failed to write to Firebase: {e}")
        return False


def _poll_firebase(timeout: int = None) -> dict | None:
    """
    Poll Firebase pipeline.json until status == COMPLETED.
    Returns the parsed response_json dict, or None on timeout.
    """
    if timeout is None:
        timeout = AI_POLLING_TIMEOUT

    deadline = time.time() + timeout
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        try:
            resp = requests.get(_firebase_pipeline_url(), timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data and data.get("status") == "COMPLETED":
                raw_json = data.get("response_json", "{}")
                if isinstance(raw_json, str):
                    result = json.loads(raw_json)
                else:
                    result = raw_json
                print(f"[classifier] Kaggle response received after {attempt} polls")
                return result
        except Exception:
            pass
        time.sleep(1)

    print(f"[classifier] [WARN] Firebase polling timed out after {timeout}s ({attempt} attempts)")
    return None


def _map_kaggle_response(kaggle_result: dict) -> dict:
    """
    Map Kaggle's output schema to the dispatch service's expected fields.

    Kaggle returns:
        severity_level (1/2/3), trauma_type, dispatch_required,
        recommended_equipment, bypass_llm, matched_trigger,
        match_method, execution_latency, system_log

    Dispatch expects:
        urgency_tier, medical_tag, severity, priority,
        ambulance_required, suspected_conditions,
        recommended_department, recommended_specialist,
        confidence, first_aid, reasoning, trauma_type
    """
    # ── Severity mapping ───────────────────────────────────────────
    sev_level = kaggle_result.get("severity_level", 3)
    if isinstance(sev_level, str):
        try:
            sev_level = int(sev_level)
        except ValueError:
            sev_level = 3
    sev_info = SEVERITY_LEVEL_MAP.get(sev_level, SEVERITY_LEVEL_MAP[3])

    # ── Trauma type ────────────────────────────────────────────────
    trauma_type = kaggle_result.get("trauma_type", "Unknown")
    if not trauma_type or trauma_type == "":
        trauma_type = "Unknown"
    medical_tag = TRAUMA_TO_SPECIALTY.get(trauma_type, "general")

    # ── Equipment -> first_aid ─────────────────────────────────────
    equipment = kaggle_result.get("recommended_equipment", [])
    if isinstance(equipment, str):
        equipment = [equipment]

    # ── Build reasoning from audit fields ──────────────────────────
    bypass = kaggle_result.get("bypass_llm", False)
    engine = "Deterministic Rules Engine (Layer 1)" if bypass else "Qwen-2.5-7B Neural Engine (Layer 2)"
    latency = kaggle_result.get("execution_latency", "N/A")
    system_log = kaggle_result.get("system_log", "")
    matched_trigger = kaggle_result.get("matched_trigger", "")
    match_method = kaggle_result.get("match_method", "")
    reasoning_parts = [
        f"Engine: {engine}",
        f"Latency: {latency}",
    ]
    if matched_trigger:
        reasoning_parts.append(f"Matched trigger: '{matched_trigger}' ({match_method})")
    if system_log:
        reasoning_parts.append(f"Log: {system_log}")
    reasoning = " | ".join(reasoning_parts)

    # ── Confidence based on match quality ──────────────────────────
    if bypass:
        confidence = 0.95  # Deterministic rules are high-confidence
    elif match_method == "exact":
        confidence = 0.92
    elif match_method == "fuzzy":
        confidence = 0.80
    else:
        confidence = 0.85

    return {
        # Core fields used by dispatch logic
        "urgency_tier":            sev_info["urgency_tier"],
        "medical_tag":             medical_tag,

        # Rich fields
        "severity":                sev_info["severity"],
        "priority":                sev_info["priority"],
        "ambulance_required":      kaggle_result.get("dispatch_required", True),
        "suspected_conditions":    [],
        "recommended_department":  "Emergency Medicine",
        "recommended_specialist":  "General",
        "confidence":              confidence,
        "first_aid":               equipment,
        "reasoning":               reasoning,
        "trauma_type":             trauma_type,
    }


def classify(raw_transcript: str) -> dict:
    """
    Submit transcript to Firebase -> wait for Kaggle/Qwen -> map response.

    Falls back to keyword matching if Firebase is unreachable or
    Kaggle doesn't respond within the timeout.
    """
    # Step 1: Submit to Firebase
    if not _submit_to_firebase(raw_transcript):
        print("[classifier] Firebase unreachable, falling back to keyword classifier")
        return _keyword_fallback(raw_transcript)

    # Step 2: Poll for Kaggle's response
    kaggle_result = _poll_firebase()
    if kaggle_result is None:
        print("[classifier] Kaggle timed out, falling back to keyword classifier")
        return _keyword_fallback(raw_transcript)

    # Step 3: Map Kaggle output to dispatch schema
    return _map_kaggle_response(kaggle_result)


def _keyword_fallback(raw_transcript: str) -> dict:
    """
    Simple keyword-based fallback when Firebase/Kaggle is unavailable.
    Keeps the system functional even without the ML model.
    """
    text = raw_transcript.lower().strip()

    # ── Determine trauma type by keywords ──────────────────────
    keyword_map = {
        "Cardiac":      ["heart", "chest pain", "cardiac", "heart attack", "palpitation"],
        "Blunt_Trauma": ["accident", "crash", "collision", "fall", "fell", "hit"],
        "Penetrating":  ["stabbed", "gunshot", "knife", "puncture"],
        "Hemorrhage":   ["bleeding", "blood", "hemorrhage"],
        "Respiratory":  ["breathing", "asthma", "choking", "suffocation", "breathless"],
        "Neurological": ["stroke", "paralysis", "speech", "numbness", "seizure"],
        "Toxicology":   ["poison", "overdose", "drugs", "pills", "vomiting"],
        "Environmental":["burn", "fire", "scald", "electrocution"],
        "Anaphylaxis":  ["allergic", "anaphylaxis", "swelling", "hives"],
    }

    trauma_type = "Unknown"
    best_score = 0
    for ttype, keywords in keyword_map.items():
        score = sum(1 for kw in keywords if kw in text)
        if score > best_score:
            best_score = score
            trauma_type = ttype

    # ── Determine severity ─────────────────────────────────────
    critical_kw = ["unconscious", "not breathing", "no pulse", "cardiac arrest",
                   "heavy bleeding", "gunshot", "stabbed", "unresponsive"]
    high_kw = ["chest pain", "severe", "heart attack", "stroke", "accident",
               "crash", "fracture", "burn", "labor", "overdose"]

    if any(kw in text for kw in critical_kw):
        severity = "Critical"
    elif any(kw in text for kw in high_kw):
        severity = "High"
    elif best_score >= 1:
        severity = "Medium"
    else:
        severity = "Low"

    return {
        "urgency_tier":            SEVERITY_TO_URGENCY[severity],
        "medical_tag":             TRAUMA_TO_SPECIALTY.get(trauma_type, "general"),
        "severity":                severity,
        "priority":                {"Critical": 1, "High": 2, "Medium": 3, "Low": 4}[severity],
        "ambulance_required":      severity in ("Critical", "High"),
        "suspected_conditions":    [],
        "recommended_department":  "Emergency Medicine",
        "recommended_specialist":  "General",
        "confidence":              0.0,
        "first_aid":               [],
        "reasoning":               "Classified by keyword fallback (Firebase/Kaggle unavailable).",
        "trauma_type":             trauma_type,
    }


def required_ambulance_tier(urgency: str) -> str | None:
    """
    Map urgency to the minimum ambulance tier needed.
    Returns 'ALS' for CRITICAL/HIGH, None (any tier) otherwise.
    """
    if urgency in ("CRITICAL", "HIGH"):
        return "ALS"
    return None

