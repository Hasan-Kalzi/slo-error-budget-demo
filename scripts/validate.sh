#!/usr/bin/env bash

# Stop immediately if a command fails, an undefined variable is used,
# or any command within a pipeline fails.
set -euo pipefail

# Preserve Linux container paths when running through Git Bash on Windows.
export MSYS2_ARG_CONV_EXCL="*"

# Check the Compose configuration, including the optional test service.
docker compose --profile test config --quiet

# Validate Prometheus's configuration and all referenced rule files.
# --no-deps avoids starting the other services for this check.
# --rm removes the validation container afterwards.
docker compose run --rm --no-deps \
  --entrypoint /bin/promtool prometheus \
  check config /etc/prometheus/prometheus.yml

# Validate Alertmanager's routing and receiver configuration.
docker compose run --rm --no-deps \
  --entrypoint /bin/amtool alertmanager \
  check-config /etc/alertmanager/alertmanager.yml

# Build the test runner and execute the integration tests.
# Compose waits for the app's healthcheck; the app remains running afterwards.
docker compose --profile test run --build --rm tests

# This message is reached only if every preceding command succeeded.
printf '\nAll validation checks passed.\n'
