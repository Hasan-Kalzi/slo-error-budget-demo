import os
import random
from threading import Lock

from fastapi import FastAPI
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse, Response


app = FastAPI(title="SLO Error-Budget Demo")

# Prometheus metrics
requests_total = Counter(
    "demo_http_requests_total",
    "Number of requests handled by the work endpoint",
    ["result"],
)

configured_failure_rate = Gauge(
    "demo_configured_failure_rate",
    "Currently configured probability of an injected failure",
)

# The failure rate starts at 0 unless configured through an environment variable.
failure_rate = float(os.getenv("INITIAL_FAILURE_RATE", "0"))
failure_rate_lock = Lock()
configured_failure_rate.set(failure_rate)


class FailureRateUpdate(BaseModel):
    failure_rate: float = Field(ge=0, le=1)


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/config")
def get_config():
    with failure_rate_lock:
        return {"failure_rate": failure_rate}


@app.put("/config/failure-rate")
def set_failure_rate(update: FailureRateUpdate):
    global failure_rate

    with failure_rate_lock:
        failure_rate = update.failure_rate
        configured_failure_rate.set(failure_rate)

    return {"failure_rate": failure_rate}


@app.get("/work")
def work():
    with failure_rate_lock:
        current_failure_rate = failure_rate

    if random.random() < current_failure_rate:
        requests_total.labels(result="error").inc()

        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "message": "Injected demo failure",
            },
        )

    requests_total.labels(result="success").inc()
    return {"status": "success"}


@app.get("/metrics")
def metrics():
    return Response(
        content=generate_latest(),
        headers={"Content-Type": CONTENT_TYPE_LATEST},
    )