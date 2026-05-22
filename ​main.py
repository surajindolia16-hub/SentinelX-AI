
# --- 1. CORE MODELS: src/core/validator.py ---
from pydantic import BaseModel, Field

class SensorData(BaseModel):
    rain_mm: float = Field(..., ge=0, le=1000)
    river_level_m: float = Field(..., ge=0, le=50)
    elevation_m: float = Field(..., ge=-10, le=8000)

# --- 2. LOGIC ENGINE: src/core/risk_engine.py ---
class RiskCalculator:
    _COEFFICIENTS = {"rain_mm": 0.55, "river_level_m": 0.35, "elevation_m": -0.10}

    def compute_risk(self, data: SensorData) -> float:
        risk = sum(getattr(data, k) * self._COEFFICIENTS[k] for k in self._COEFFICIENTS)
        return max(0.0, min(100.0, risk))

# --- 3. INFRASTRUCTURE: src/services/hydrology.py ---
import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("sentinelx")

class HydrologyService:
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def fetch_sensor_data(self, lat: float, lon: float) -> dict:
        # Replace with your actual production endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            try:
                resp = await client.get(f"https://api.disaster-sensor.gov/v1/data?lat={lat}&lon={lon}")
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPError as e:
                logger.error(f"Hydrology API Failure: {e}")
                raise

# --- 4. EXECUTION FLOW: src/main.py ---
import asyncio
from src.core.validator import SensorData
from src.core.risk_engine import RiskCalculator
from src.services.hydrology import HydrologyService

async def run_system():
    # Setup
    svc = HydrologyService()
    calc = RiskCalculator()
    
    # Workflow
    raw_data = await svc.fetch_sensor_data(27.17, 78.00)
    valid_data = SensorData(**raw_data)
    risk_score = calc.compute_risk(valid_data)
    
    print(f"Computed Risk Score: {risk_score:.2f}")

if __name__ == "__main__":
    asyncio.run(run_system())
