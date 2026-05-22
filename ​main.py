import os
import time
import logging
from typing import TypedDict, List, Dict, Annotated

import httpx
from motor.motor_asyncio import AsyncIOMotorClient
from langgraph.graph import StateGraph, END
import operator

# -------------------------
# LOGGING / OBSERVABILITY
# -------------------------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SentinelX")


# -------------------------
# STATE (SYSTEM MEMORY)
# -------------------------
class SentinelState(TypedDict):
    location: Dict
    sensor_data: Dict
    risk_score: float
    historical_context: List[Dict]
    resources: List[Dict]
    decision: str
    audit: Annotated[List[str], operator.add]


# -------------------------
# OBSERVABILITY (LIGHTWEIGHT OTEL STYLE)
# -------------------------
class Span:
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.time()
        logger.info(f"[SPAN START] {self.name}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        logger.info(f"[SPAN END] {self.name} | {time.time() - self.start:.4f}s")


def tracer(name):
    return Span(name)


# -------------------------
# 1. WEATHER INGESTION NODE
# -------------------------
async def weather_node(state: SentinelState):
    with tracer("weather_fetch"):

        async with httpx.AsyncClient() as client:
            # simulated API (replace with real OpenWeather)
            data = {
                "rain": 80,
                "river": 70,
                "elev": 20
            }

        return {
            "sensor_data": data,
            "audit": ["Weather data ingested"]
        }


# -------------------------
# 2. SEMANTIC MEMORY (VECTOR STYLE MOCK)
# -------------------------
async def memory_node(state: SentinelState):
    with tracer("historical_memory"):

        client = AsyncIOMotorClient(os.getenv("MONGO_URI"))
        db = client.sentinel

        # simplified aggregation (vector search concept hook)
        history = await db.disasters.find(
            {"sector": state["location"]["sector"]}
        ).to_list(length=10)

        return {
            "historical_context": history,
            "audit": ["Historical patterns retrieved"]
        }


# -------------------------
# 3. PURE MATHEMATICAL RISK ENGINE
# -------------------------
def risk_node(state: SentinelState):
    with tracer("risk_engine"):

        data = state["sensor_data"]

        # deterministic formula (NO AI)
        score = (
            data["rain"] * 0.6 +
            data["river"] * 0.4 -
            data["elev"] * 0.1
        )

        score = max(0, min(100, score))

        return {
            "risk_score": score,
            "audit": [f"Risk computed deterministically: {score}"]
        }


# -------------------------
# 4. DECISION ENGINE (RULE BASED)
# -------------------------
def decision_node(state: SentinelState):
    with tracer("decision_engine"):

        score = state["risk_score"]

        if score >= 75:
            decision = "CRITICAL_EVACUATION"
        elif score >= 50:
            decision = "HIGH_ALERT"
        elif score >= 25:
            decision = "MONITOR"
        else:
            decision = "NORMAL"

        return {
            "decision": decision,
            "audit": [f"Decision generated: {decision}"]
        }


# -------------------------
# 5. RESOURCE ENGINE (RULE BASED)
# -------------------------
def resource_node(state: SentinelState):
    with tracer("resource_engine"):

        score = state["risk_score"]

        if score > 70:
            resources = [
                {"type": "Shelter", "priority": "HIGH"},
                {"type": "Hospital", "priority": "HIGH"},
                {"type": "Evac Route", "priority": "ACTIVE"}
            ]
        else:
            resources = [
                {"type": "Monitoring Mode", "priority": "LOW"}
            ]

        return {
            "resources": resources,
            "audit": ["Resources allocated based on risk score"]
        }


# -------------------------
# 6. FINAL REPORT (NO AI)
# -------------------------
def report_node(state: SentinelState):
    with tracer("report_generator"):

        report = {
            "location": state["location"],
            "risk_score": state["risk_score"],
            "decision": state["decision"],
            "resources": state["resources"],
            "historical_events": len(state["historical_context"]),
            "system": "SentinelX Deterministic Disaster Engine"
        }

        logger.info("Final report generated")

        return {"report": report}


# -------------------------
# GRAPH WORKFLOW
# -------------------------
workflow = StateGraph(SentinelState)

workflow.add_node("weather", weather_node)
workflow.add_node("memory", memory_node)
workflow.add_node("risk", risk_node)
workflow.add_node("decision", decision_node)
workflow.add_node("resource", resource_node)
workflow.add_node("report", report_node)

workflow.set_entry_point("weather")

workflow.add_edge("weather", "memory")
workflow.add_edge("memory", "risk")
workflow.add_edge("risk", "decision")
workflow.add_edge("decision", "resource")
workflow.add_edge("resource", "report")
workflow.add_edge("report", END)

app = workflow.compile()
