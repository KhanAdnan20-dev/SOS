"""
AI Model Microservice
──────────────────────
A thin FastAPI wrapper around your Qwen2.5-7B-Instruct model.

Copy your notebook's model-loading and inference code into this file
where indicated by the TODO markers.

Run separately:  python ai_server.py   (starts on port 5000)
The dispatch backend calls this at http://localhost:5000/classify
"""

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import json
import re

# ────────────────────────────────────────────────────────────────
#  TODO: Paste your model loading code here
# ────────────────────────────────────────────────────────────────
from transformers import AutoTokenizer, AutoModelForCausalLM

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_NEW_TOKENS = 512

print("🔄 Loading model... (this may take a minute)")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    torch_dtype=torch.float16,
    trust_remote_code=True,
)
print("✅ Model loaded!")


# ────────────────────────────────────────────────────────────────
#  TODO: Paste your generate_json and process_response functions
#        from your notebook here.
#
#  They should look something like this (replace with your actual code):
# ────────────────────────────────────────────────────────────────

def generate_json(symptoms: str, evidence: str = "", max_new_tokens: int = MAX_NEW_TOKENS) -> str:
    """
    TODO: Replace this with your actual generate_json function from
    your notebook. The function below is a placeholder structure.

    Your real function likely builds a prompt, tokenizes it,
    runs model.generate(), and decodes the output.
    """
    # ── Build the prompt (replace with your actual prompt template) ──
    prompt = f"""You are a medical triage AI. Analyze the following symptoms and return a JSON response.

Symptoms: {symptoms}
{"Evidence: " + evidence if evidence else ""}

Return a JSON object with these fields:
- severity: Critical/High/Medium/Low
- priority: 1-4
- ambulance_required: true/false
- suspected_conditions: list of strings
- recommended_department: string
- recommended_specialist: string
- confidence: float 0.0-1.0
- first_aid: list of strings
- reasoning: string
- trauma_type: one of Cardiac/Penetrating/Respiratory/Hemorrhage/Neurological/Toxicology/Blunt_Trauma/Anaphylaxis/Environmental/Unknown

Respond with ONLY valid JSON, no other text."""

    messages = [
        {"role": "system", "content": "You are a medical triage assistant. Always respond with valid JSON only."},
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=0.3,
            do_sample=True,
        )

    # Decode only the new tokens (skip the prompt)
    generated = outputs[0][inputs["input_ids"].shape[-1]:]
    return tokenizer.decode(generated, skip_special_tokens=True)


def process_response(raw_output: str) -> dict:
    """
    TODO: Replace with your actual process_response function.
    This placeholder extracts JSON from the model's raw text output.
    """
    # Try to find JSON in the output
    try:
        # Look for JSON block
        json_match = re.search(r'\{[\s\S]*\}', raw_output)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = json.loads(raw_output)
    except json.JSONDecodeError:
        # Fallback if parsing fails
        result = {
            "severity": "Unknown",
            "priority": 4,
            "ambulance_required": True,
            "suspected_conditions": ["Unable to classify"],
            "recommended_department": "Emergency Medicine",
            "recommended_specialist": "General",
            "confidence": 0.0,
            "first_aid": [],
            "reasoning": "Model output could not be parsed.",
            "trauma_type": "Unknown",
        }

    # ── Validate / fill defaults ───────────────────────────────
    valid_severities = {"Critical", "High", "Medium", "Low"}
    if result.get("severity") not in valid_severities:
        result["severity"] = "Unknown"

    valid_trauma = {
        "Cardiac", "Penetrating", "Respiratory", "Hemorrhage",
        "Neurological", "Toxicology", "Blunt_Trauma", "Anaphylaxis",
        "Environmental", "Unknown",
    }
    if result.get("trauma_type") not in valid_trauma:
        result["trauma_type"] = "Unknown"

    result.setdefault("priority", 4)
    result.setdefault("ambulance_required", True)
    result.setdefault("suspected_conditions", [])
    result.setdefault("recommended_department", "Emergency Medicine")
    result.setdefault("recommended_specialist", "General")
    result.setdefault("confidence", 0.0)
    result.setdefault("first_aid", [])
    result.setdefault("reasoning", "")
    result.setdefault("trauma_type", "Unknown")

    return result


# ────────────────────────────────────────────────────────────────
#  FastAPI Wrapper
# ────────────────────────────────────────────────────────────────

app = FastAPI(title="SOS AI Triage Model", version="1.0.0")


class ClassifyRequest(BaseModel):
    symptoms: str = Field(..., description="Raw distress transcript / symptom text")
    evidence: str = Field("", description="Optional additional evidence")


class ClassifyResponse(BaseModel):
    severity: str
    priority: int
    ambulance_required: bool
    suspected_conditions: list[str]
    recommended_department: str
    recommended_specialist: str
    confidence: float
    first_aid: list[str]
    reasoning: str
    trauma_type: str


@app.post("/classify", response_model=ClassifyResponse)
async def classify_endpoint(req: ClassifyRequest):
    """Run the AI triage model on the given symptoms."""
    try:
        raw = generate_json(req.symptoms, req.evidence)
        result = process_response(raw)
        return ClassifyResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Model inference failed: {str(e)}")


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME}


if __name__ == "__main__":
    print("=" * 60)
    print("  🧠  SOS AI Triage Model Server")
    print("  📡  http://localhost:5000")
    print("  📄  http://localhost:5000/docs")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=5000)
