"""SecureFlow Traffic Signal Controller Simulator.

Simulates physical intersection signal controllers (TB4):
- Verifies signed HMAC-SHA256 timing plan commands
- Cycles signal phases (NS -> Y1 -> R1 -> EW -> Y2 -> R2)
- Reverts to fixed-time fallback plan on timeout or loss of backend communication
"""
import hashlib
import hmac
import time
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Request
import uvicorn

CONTROLLER_KEY = b"controller-secret-hmac-key-256bit-min-32-chars"
DEFAULT_PLAN = {"ns": 45, "ew": 40, "yellow": 3, "allred": 2}

app = FastAPI(title="SecureFlow Signal Controller Simulator")

current_plan = dict(DEFAULT_PLAN)
last_command_time = time.time()


@app.post("/api/controller/apply")
async def apply_signal_command(request: Request):
    """Receive and verify HMAC-signed signal plan command."""
    global current_plan, last_command_time

    body_bytes = await request.body()
    signature_header = request.headers.get("X-Controller-Signature")

    if not signature_header:
        raise HTTPException(status_code=401, detail="Unsigned controller command rejected.")

    # Verify HMAC-SHA256 signature
    expected_sig = hmac.new(CONTROLLER_KEY, body_bytes, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_sig.lower(), signature_header.lower()):
        raise HTTPException(status_code=401, detail="Invalid controller command signature.")

    payload = await request.json()
    new_plan = payload.get("plan")
    if not new_plan:
        raise HTTPException(status_code=400, detail="Missing plan payload.")

    current_plan = dict(new_plan)
    last_command_time = time.time()
    return {"status": "applied", "plan": current_plan}


@app.get("/api/controller/status")
async def get_controller_status():
    """Report current active signal timing and phase cycle."""
    global current_plan, last_command_time

    # Failsafe fallback if no communication for > 30 minutes
    if time.time() - last_command_time > 1800:
        current_plan = dict(DEFAULT_PLAN)

    return {
        "status": "online",
        "plan": current_plan,
        "failsafe_active": current_plan == DEFAULT_PLAN
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8010)
