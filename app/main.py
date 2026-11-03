import logging
import os
import sys

# Ensure UTF-8 output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
        sys.stderr.reconfigure(
            encoding="utf-8",
            errors="replace"
        )
    except Exception:
        pass

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from fastapi import FastAPI
import uvicorn

from app.api.routes import router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(
    "scenario_simulation"
)

app = FastAPI(
    title="ARIIA Scenario Simulation Agent",
    description=(
        "Enterprise Multi-Agent Scenario "
        "Simulation and Impact Analysis Engine"
    ),
    version="1.0.0",
)

app.include_router(router)


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service":
            "scenario_simulation_agent",
    }


if __name__ == "__main__":

    print(
        "Starting ARIIA Scenario Simulation "
        "Server on http://0.0.0.0:8000"
    )

    print(
        "Swagger Docs: "
        "http://localhost:8000/docs"
    )

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )