#!/usr/bin/env bash

# Stop if a command fails, a variable is undefined, or a pipeline fails.
set -euo pipefail

# Find this script's directory, then run Compose from the repository root.
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR/.."

# Update the application's failure probability through its HTTP API.
set_failure_rate() {
    # Read the probability supplied by the selected demo command.
    local rate="$1"

    # Send JSON; report HTTP/network errors and limit the request to 10 seconds.
    curl --fail --show-error --silent --max-time 10 \
        --request PUT \
        --header "Content-Type: application/json" \
        --data "{\"failure_rate\": $rate}" \
        "http://localhost:8000/config/failure-rate"

    # Put the next terminal message on a new line.
    printf '\n'
}

# Choose the action from the first command-line argument.
case "${1:-}" in
    start)
        # Build and start the demo; wait for running/healthy services.
        docker compose up --build --detach --wait --wait-timeout 90

        # Start with successful requests, including when reusing running containers.
        set_failure_rate 0
        printf 'Demo started.\nPrometheus: http://localhost:9090\nAlertmanager: http://localhost:9093\n'
        ;;
    fail)
        # Give each work request a 20% probability of an injected failure.
        set_failure_rate 0.2
        printf 'Failure probability set to 20%%.\n'
        ;;
    recover)
        # Disable injected failures; the rolling metrics need time to recover.
        set_failure_rate 0
        printf 'Injected failures disabled.\n'
        ;;
    stop)
        # Stop and remove the demo containers and Compose network.
        docker compose down
        ;;
    *)
        # Explain the valid commands when the argument is missing or unknown.
        printf 'Usage: bash scripts/demo.sh {start|fail|recover|stop}\n' >&2
        exit 1
        ;;
esac