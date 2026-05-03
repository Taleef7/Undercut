from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import duckdb
from pathlib import Path
from sim.engine import UndercutEngine
from sim.scoring import StrategyDecision, ScenarioContext

app = FastAPI(title="Undercut API")
ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "undercut.db"

@app.get("/")
def read_root():
    return {"message": "Undercut API is running"}

@app.get("/scenarios")
def get_scenarios():
    conn = duckdb.connect(str(DB_PATH))
    scenarios = conn.execute("SELECT * FROM race_state_decision_point").fetchall()
    conn.close()
    return {"scenarios": scenarios}

class DecisionRequest(BaseModel):
    action: str
    compound: Optional[str] = None

@app.post("/scenarios/{decision_id}/simulate")
def simulate_decision(decision_id: str, request: DecisionRequest):
    conn = duckdb.connect(str(DB_PATH))
    dp = conn.execute(
        "SELECT * FROM race_state_decision_point WHERE decision_point_id = ?", 
        (decision_id,)
    ).fetchone()
    conn.close()
    
    if not dp:
        raise HTTPException(status_code=404, detail="Scenario not found")
        
    # Create context from DB record
    context = ScenarioContext(
        driver=dp[2],
        lap=dp[3],
        position=1, # Simplified for MVP
        compound="medium", # Simplified
        stint_age=15, # Simplified
        gap_ahead=1.2,
        gap_behind=0.8,
        laps_remaining=10
    )
    
    engine = UndercutEngine()
    result = engine.evaluate_strategy(
        StrategyDecision(action=request.action, compound=request.compound),
        context,
        dp[8] # Historical decision
    )
    return result
