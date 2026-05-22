# SentinelX AI: Autonomous Disaster Intelligence System
# Developed for Google Cloud Rapid Agent Hackathon 2026

import os
import json
import time
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import google.generativeai as genai
from pymongo import MongoClient

# Initialize App
app = FastAPI(title="SentinelX AI")

# --- Configuration ---
# Note: Use environment variables for production security
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
client = MongoClient(os.getenv("MONGODB_URI"))
db = client.disaster_data

# --- Data Models ---
class DisasterInput(BaseModel):
    username: str
    dob: str  # YYYY-MM-DD
    location: str
    rainfall_mm: float
    river_level: float
    temperature: float

# --- Agent 1: Reasoning Agent (The Brain) ---
class ReasoningAgent:
    def get_assessment(self, data: dict):
        model = genai.GenerativeModel('gemini-1.5-flash')
        prompt = f"""
        Analyze disaster risk for {data['location']}. 
        User Age Calculation: 2026 - {int(data['dob'].split('-')[0])}.
        Inputs: {data}. 
        Return ONLY a JSON with 'risk_score' (0-100), 'reasoning', and 'safety_instruction'.
        """
        response = model.generate_content(prompt)
        # Cleaning the response to get pure JSON
        clean_text = response.text.replace('```json', '').replace('```', '')
        return json.loads(clean_text)

# --- Agent 2: Decision Agent ---
class DecisionAgent:
    def get_action(self, score: float):
        if score > 70: return "CRITICAL: Immediate Evacuation Needed"
        if score > 40: return "MEDIUM: Increase Monitoring"
        return "LOW: Normal Status"

# --- Coordinator: The Orchestrator ---
class SentinelXCoordinator:
    def __init__(self):
        self.reasoner = ReasoningAgent()
        self.decision = DecisionAgent()

    def process_data(self, data: DisasterInput):
        # 1. Reasoning
        assessment = self.reasoner.get_assessment(data.dict())
        
        # 2. Decision
        action = self.decision.get_action(assessment['risk_score'])
        
        # 3. Persistence
        report = {
            **data.dict(),
            **assessment,
            "action": action,
            "timestamp": time.ctime()
        }
        db.reports.insert_one(report)
        
        return report

system = SentinelXCoordinator()

# --- API Endpoints ---
@app.post("/analyze")
def analyze(data: DisasterInput):
    try:
        return system.process_data(data)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"System Error: {str(e)}")

@app.get("/")
def health_check():
    return {"status": "SentinelX AI is running and ready for deployment"}
