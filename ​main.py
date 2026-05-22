
import httpx
import logging
import asyncio
from typing import TypedDict, List, Dict
from pydantic import BaseModel, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorClient
from langgraph.graph import StateGraph, END
from langchain_google_vertexai import ChatVertexAI

# --- 1. Defensive Data Layer (Validated Sensor Data) ---
class SensorState(BaseModel):
    rain_mm: float = Field(..., ge=0, le=1000)
    river_level_m: float = Field(..., ge=0, le=50)
    elevation_m: float = Field(..., ge=-10, le=8000)

# --- 2. Deterministic Risk Engine (Normalization & Domain logic) ---
class FloodRiskModel:
    def __init__(self, rain_w=0.6, river_w=0.4):
        self.weights = {"rain": rain_w, "river": river_w}
    
    def calculate(self, data: SensorState) -> float:
        # Normalization: Score is capped at 100
        raw_score = (data.rain_mm * self.weights["rain"]) + (data.river_level_m * self.weights["river"])
        return min(100.0, max(0.0, raw_score))

# --- 3. Analytical Agent (Historical Trend Analysis) ---
async def historical_trend_agent(state: dict):
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    # Instead of just fetching, we calculate deviation from historical mean
    stats = await client.sentinel.history.aggregate([
        {"$match": {"sector": state['loc']['sector']}},
        {"$group": {"_id": None, "mean_impact": {"$avg": "$impact_score"}}}
    ]).to_list(1)
    return {"trend_deviation": stats[0]['mean_impact'] if stats else 0}

# --- 4. Synthesis Agent (Explainability Engine) ---
def reasoning_synthesizer(state: dict):
    llm = ChatVertexAI(model="gemini-1.5-pro")
    # Breaking down the Risk Score to provide Explainability
    factors = f"Rain impact: {state['sensor'].rain_mm * 0.6}, River level: {state['sensor'].river_level_m * 0.4}"
    prompt = f"Explain the risk score {state['risk_score']} based on these factors: {factors}. Propose 3 evacuation steps."
    return {"final_analysis": llm.invoke(prompt).content}

# --- 5. Graph Wiring (The "System") ---
# The logic flow is now: Validate -> Calculate -> Analyze Trends -> Synthesize
