import os
import time
import logging
import asyncio
import httpx
from fastapi import FastAPI
from motor.motor_asyncio import AsyncIOMotorClient

app = FastAPI(title="SentinelX - Disaster Risk Agent")

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("sentinelx")


def info(msg):
    log.info(msg)


# -------------------------
# WEATHER (REAL API)
# -------------------------
async def weather(lat, lon):
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "current_weather": True
                }
            )
        data = r.json().get("current_weather", {})
        return {
            "temp": data.get("temperature", 25),
            "wind": data.get("windspeed", 10)
        }
    except:
        info("weather fallback used")
        return {"temp": 25, "wind": 10}


# -------------------------
# MEMORY (MongoDB)
# -------------------------
async def history(region):
    try:
        client = AsyncIOMotorClient(os.getenv("MONGO_URI", "mongodb://localhost:27017"))
        db = client.sentinelx

        return await db.disasters.find(
            {"region": region}
        ).to_list(5)

    except:
        info("mongo fallback used")
        return []


# -------------------------
# SIMPLE RISK THINKING
# -------------------------
def risk_score(weather, hist_len):
    score = (weather["wind"] * 0.7) + (weather["temp"] * 0.2) + (hist_len * 6)
    return min(round(score, 2), 100)


# -------------------------
# DECISION LOGIC
# -------------------------
def decision(score):
    if score > 80:
        return "EVACUATION"
    if score > 60:
        return "HIGH_ALERT"
    if score > 30:
        return "WATCH"
    return "SAFE"


# -------------------------
# MAIN PIPELINE
# -------------------------
@app.post("/analyze")
async def analyze(payload: dict):

    loc = payload.get("location", {})
    region = loc.get("region", "unknown")

    info(f"processing region: {region}")

    weather_task = weather(loc.get("lat"), loc.get("lon"))
    history_task = history(region)

    w, h = await asyncio.gather(weather_task, history_task)

    score = risk_score(w, len(h))
    action = decision(score)

    return {
        "system": "SentinelX",
        "region": region,
        "risk": score,
        "decision": action,
        "weather": w,
        "history_count": len(h),
        "note": "simple real-time risk scoring system"
    }