import os

import pytest
import requests


# Read the application address from the environment.
# The default value works inside the Docker Compose network.
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://app:8000")

# Prevent a failed request from making the test suite wait indefinitely.
REQUEST_TIMEOUT_SECONDS = 3


def set_failure_rate(value: float) -> requests.Response:
    """Set the application's injected failure rate and return the response."""

    return requests.put(
        f"{APP_BASE_URL}/config/failure-rate",
        json={"failure_rate": value},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )


@pytest.fixture(autouse=True)
def reset_failure_rate():
    """Reset the failure rate before and after every test.

    This isolates the tests so that one test cannot affect the next one.
    """

    # Start every test with deterministic successful behaviour.
    response = set_failure_rate(0)
    assert response.status_code == 200

    # Run the test.
    yield

    # Restore normal behaviour even if the test changed the failure rate.
    response = set_failure_rate(0)
    assert response.status_code == 200


def test_health_endpoint():
    """Verify that the application reports itself as healthy."""

    response = requests.get(
        f"{APP_BASE_URL}/health",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_failure_rate_can_be_updated_and_read():
    """Verify that the runtime failure configuration can be changed."""

    update_response = set_failure_rate(0.25)

    assert update_response.status_code == 200
    assert update_response.json() == {"failure_rate": 0.25}

    config_response = requests.get(
        f"{APP_BASE_URL}/config",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    assert config_response.status_code == 200
    assert config_response.json() == {"failure_rate": 0.25}


@pytest.mark.parametrize("invalid_rate", [-0.1, 1.1])
def test_invalid_failure_rates_are_rejected(invalid_rate):
    """Verify that failure rates outside the range 0–1 are rejected."""

    response = set_failure_rate(invalid_rate)

    # FastAPI returns 422 when Pydantic validation rejects the request body.
    assert response.status_code == 422


def test_work_succeeds_with_zero_failure_rate():
    """Verify deterministic success when failure injection is disabled."""

    set_failure_rate(0)

    response = requests.get(
        f"{APP_BASE_URL}/work",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "success"}


def test_work_fails_with_full_failure_rate():
    """Verify deterministic failure when the failure rate is set to 100%."""

    set_failure_rate(1)

    response = requests.get(
        f"{APP_BASE_URL}/work",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    assert response.status_code == 500
    assert response.json() == {
        "status": "error",
        "message": "Injected demo failure",
    }


def test_metrics_endpoint_exposes_demo_metrics():
    """Verify that Prometheus can read the application's custom metrics."""

    # Generate one successful request so the success-labelled counter exists.
    requests.get(
        f"{APP_BASE_URL}/work",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    response = requests.get(
        f"{APP_BASE_URL}/metrics",
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    assert response.status_code == 200
    assert "text/plain" in response.headers["Content-Type"]

    metrics = response.text

    assert 'demo_http_requests_total{result="success"}' in metrics
    assert "demo_configured_failure_rate" in metrics
