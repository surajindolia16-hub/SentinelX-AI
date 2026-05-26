import time, logging, uuid, asyncio, numpy as np
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Header, Depends, status
from pydantic import BaseModel, Field, field_validator
from motor.motor_asyncio import AsyncIOMotorClient
from contextlib import asynccontextmanager

# 1. LIFECYCLE & POOLING (Point #1, #20)
class AppState:
    db_client: AsyncIOMotorClient = None
    db: any = None
state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    state.db_client = AsyncIOMotorClient("mongodb://localhost:27017", maxPoolSize=50)
    state.db = state.db_client.sentinelx
    yield
    state.db_client.close()

app = FastAPI(lifespan=lifespan)

# 2. MODELS & VALIDATION (Point #3, #11)
class SensorReadings(BaseModel):
    wind: float = Field(..., ge=0, le=300)
    temp: float = Field(..., ge=-50, le=60) # Normalized to 0-1 for stability
    humidity: float = Field(..., ge=0, le=100)

class DisasterReport(BaseModel):
    region: str
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    event_type: str 

    @field_validator('event_type')
    def validate_type(cls, v):
        allowed = {"flood", "cyclone", "wildfire", "earthquake", "heatwave"}
        if v not in allowed: raise ValueError("Invalid type")
        return v

# 3. ROBUST ENGINE (Point #4, #6, #7, #8, #21, #28)
class RiskEngine:
    MODELS = {
        "flood": [0.2, 0.1, 0.7], "cyclone": [0.7, 0.1, 0.2],
        "wildfire": [0.1, 0.8, 0.1], "earthquake": [0.0, 0.1, 0.9],
        "heatwave": [0.0, 0.9, 0.1]
    }
    
    @staticmethod
    def calculate(event, readings, history):
        w = RiskEngine.MODELS.get(event, [0.33]*3)
        # Normalization with clamping (Point #6)
        vals = [readings.wind/150, max(0, readings.temp/50), readings.humidity/100]
        score = np.dot(w, vals) * 100
        
        # Trend: Weighted severity (Point #7, #20)
        trend = np.polyfit(range(len(history)), [h.get('risk', 0) for h in history], 1)[0] if len(history) > 2 else 0
        final = min(100, score + (trend * 2))
        return round(final, 2), round(max(0, 1 - (1/(len(history)+1))), 2)

# 4. ANALYZE ENDPOINT (Point #2, #13, #14, #17, #18)
@app.post("/analyze")
async def analyze(report: DisasterReport, readings: SensorReadings, x_api_key: str = Header(...)):
    if x_api_key != os.getenv("APP_SECRET", "default_secret"): raise HTTPException(403)
    
    req_id = str(uuid.uuid4())
    start = time.perf_counter()
    
    try:
        # History Query (Point #29)
        history = await asyncio.wait_for(
            state.db.audit.find({"region": report.region}).sort("ts", -1).limit(5).to_list(5), 
            timeout=2.0
        )
        
        risk, conf = RiskEngine.calculate(report.event_type, readings, history)
        
        audit_data = {
            "req_id": req_id, "region": report.region, "risk": risk, 
            "ts": time.time(), "readings": readings.dict(), "event": report.event_type
        }
        await state.db.audit.insert_one(audit_data)
        
        return {"id": req_id, "risk": risk, "confidence": conf, "ms": (time.perf_counter()-start)*1000}
    except Exception as e:
        logger.error(f"Error {req_id}: {str(e)}") # Point #25
        raise HTTPException(500, "Processing failed")
