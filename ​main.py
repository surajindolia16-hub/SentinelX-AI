import httpx
import logging
from pydantic import BaseModel, Field

# 1. Domain Object: Reality-based constraints
class SensorData(BaseModel):
    rain: float = Field(..., gt=-1)
    river: float = Field(..., gt=-1)
    elevation: float

# 2. Logic: Sirf math, koi buzzword nahi
class RiskCalc:
    # IMD-standard weights
    WEIGHTS = {"rain": 0.6, "river": 0.3, "elevation": -0.1}

    @staticmethod
    def get_score(data: SensorData) -> float:
        # Standard weighted linear combination
        score = (data.rain * 0.6) + (data.river * 0.3) + (data.elevation * -0.1)
        return max(0.0, min(100.0, score))

# 3. Execution: Direct API call, koi 'Retry' library ka tamasha nahi
async def get_risk(lat: float, lon: float):
    async with httpx.AsyncClient() as client:
        # Direct call
        res = await client.get(f"https://api.sensors.gov/read?lat={lat}&lon={lon}")
        data = SensorData(**res.json())
        return RiskCalc.get_score(data)

# 4. Main: Simple entry point
if __name__ == "__main__":
    import asyncio
    print(asyncio.run(get_risk(27.17, 78.00)))

