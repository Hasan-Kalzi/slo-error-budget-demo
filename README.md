# SLO Error-Budget Demo

A local demonstration of how request failures affect an availability SLI and an error-budget burn rate. A FastAPI service exposes request counters, a load generator sends traffic, Prometheus calculates the burn rate, and Alertmanager displays the resulting alert.

Failure injection and recovery are controlled manually without restarting the application.

## Architecture

| Service | Role | Local address |
| --- | --- | --- |
| `app` | Handles `/work`, injects failures, and exposes `/metrics`. | <http://localhost:8000/docs> |
| `load-generator` | Continuously calls the app's `/work` endpoint. | Internal Compose network only |
| `prometheus` | Scrapes metrics, evaluates recording rules, and sends alerts to Alertmanager. | <http://localhost:9090> |
| `alertmanager` | Groups received alerts and displays their state. | <http://localhost:9093> |

The load generator waits 0.1 seconds between requests, in addition to the request duration. Prometheus scrapes and evaluates rules every 2 seconds. The optional `tests` service runs only through the `test` profile.

## SLI, SLO target, error budget, and burn rate

- **SLI:** the proportion of handled `/work` requests that succeed with HTTP 200. Injected failures return HTTP 500. Health, configuration, and metrics requests are excluded from this counter.
- **SLO target:** 99% successful `/work` requests.
- **Allowed error fraction:** `1 - 0.99 = 0.01`, or 1%. For example, a reporting period containing 1,000 requests would allow 10 failures.
- **Burn rate:** the observed error ratio divided by the allowed error fraction.

Prometheus estimates the recent error ratio using request-counter rates over a rolling 30-second window:

```text
error_ratio = failed_request_rate / total_request_rate
burn_rate   = error_ratio / 0.01
```

The denominator in the configured error-ratio rule is clamped to a small positive value to avoid division by zero.

| Observed error ratio | Burn rate | Meaning |
| --- | --- | --- |
| 0% | 0 | No budget consumption from handled request failures |
| 1% | 1 | Errors occur at the allowed fraction |
| 20% | 20 | Errors occur at 20 times the allowed fraction |

The `ErrorBudgetBurning` alert becomes **Firing** when the burn rate remains greater than 1 for 10 seconds. This threshold and the short measurement window make the behaviour visible during a live demo.

The 30-second window is an alert measurement window. This project does not calculate a remaining error budget over a complete reporting period. A firing alert indicates excessive recent burn; it does not establish that the entire budget has been exhausted.

## Requirements

- Docker Engine and Docker Compose with support for `docker compose up --wait`.
- Bash, Git, and `curl` on the host.
- Available host ports 8000, 9090, and 9093.
- Internet access for the initial image and dependency downloads.

On Windows, use Git Bash and ensure Docker Desktop's Linux engine is running. Python and the test dependencies run inside containers; a host Python installation is unnecessary.

## Get the code

```bash
# Clone the repository and enter its root directory.
git clone https://github.com/Hasan-Kalzi/slo-error-budget-demo.git
cd slo-error-budget-demo
```

When reviewing a pull request, check out its branch before running the scripts below. Run all documented commands from the repository root.

## Validate the configuration and application

Run validation before the demo. The tests change the failure configuration and generate requests, which would interfere with the live walkthrough.

```bash
# Validate Compose, Prometheus, Alertmanager, and the application API.
bash scripts/validate.sh
```

The script stops on the first failed check. It performs:

1. Compose configuration validation, including the optional test service.
2. Prometheus configuration and referenced rule-file validation with `promtool`.
3. Alertmanager configuration validation with `amtool`.
4. Seven HTTP integration tests against the app container.

The tests cover health responses, configuration updates and reads, rejection of two out-of-range failure rates, deterministic success at 0% failures, deterministic failure at 100%, and metrics exposure.

Successful output ends with `7 passed` and `All validation checks passed.` The test container is removed, while the app remains running. Stop it before beginning a fresh demo:

```bash
# Remove the validation app container and its Compose network.
bash scripts/demo.sh stop
```

The validation script disables Git Bash path conversion for Linux container paths. The repository's `.gitattributes` keeps Bash scripts using LF line endings.

## Live demo

### 1. Start with failure injection disabled

```bash
# Build and start the demo services, then set the failure probability to zero.
bash scripts/demo.sh start

# Inspect the running services and application healthcheck.
docker compose ps
```

Open [Prometheus targets](http://localhost:9090/targets) and check that `app:8000` under the `demo-app` job is **UP**. Open [Prometheus alerts](http://localhost:9090/alerts) and [Alertmanager](http://localhost:9093) to follow alert state changes.

The app's `/health` endpoint checks that the app responds. It remains healthy during injected `/work` failures; Docker health and the request-success SLI measure different things.

Useful expressions in the Prometheus query interface:

| PromQL expression | What it shows |
| --- | --- |
| `demo_configured_failure_rate` | The configured failure probability |
| `demo:error_ratio:rate30s` | The observed error ratio over the recent window |
| `demo:error_budget_burn_rate:rate30s` | The recent error-budget burn rate |

On a fresh app, the error-ratio and burn-rate queries may initially return no data because the error-labelled counter is created only after the first failed request. This initial absence does not demonstrate a measured zero error ratio.

### 2. Inject failures and observe the alert

```bash
# Give each work request a 20% probability of returning HTTP 500.
bash scripts/demo.sh fail
```

Expected API response: `{"failure_rate":0.2}`.

Allow roughly a minute for observation. The measured error ratio should fluctuate around 0.2 under sustained traffic, and the burn rate around 20. These values are estimates from random request outcomes, rather than fixed readings.

Check that `ErrorBudgetBurning` progresses from **Pending** to **Firing** in Prometheus and then appears in Alertmanager. Leave failure injection enabled until the alert is visible in both interfaces.

### 3. Recover and observe resolution

```bash
# Disable new injected failures without restarting the application.
bash scripts/demo.sh recover
```

Expected API response: `{"failure_rate":0.0}`.

New `/work` requests succeed, while earlier failures remain in the rolling measurement window until they age out. Allow roughly a minute and refresh the interfaces as needed. The burn rate should fall below the threshold, the alert should become **Inactive** in Prometheus, and it should disappear from Alertmanager's active alerts.

### 4. Stop the demo

```bash
# Stop and remove the demo containers and Compose network.
bash scripts/demo.sh stop
```

## Files

| Path | Purpose |
| --- | --- |
| [app/main.py](app/main.py) | API, failure injection, and application metrics |
| [load-generator/load.py](load-generator/load.py) | Continuous request generation |
| [docker-compose.yml](docker-compose.yml) | Service builds, images, networking, and test profile |
| [prometheus/prometheus.yml](prometheus/prometheus.yml) | Scraping and Alertmanager connection |
| [prometheus/alert-rules.yml](prometheus/alert-rules.yml) | Error ratio, burn rate, and alert rules |
| [alertmanager/alertmanager.yml](alertmanager/alertmanager.yml) | Alert grouping and receiver configuration |
| [scripts/demo.sh](scripts/demo.sh) | Start, inject failures, recover, and stop |
| [scripts/validate.sh](scripts/validate.sh) | Configuration checks and integration-test execution |
| [tests/test_app.py](tests/test_app.py) | Seven application integration-test cases |

## Limitations

- Only handled `/work` successes and injected failures contribute to the SLI. Connection failures and requests that never reach the app are outside this measurement.
- The demo uses one short window and a low alert threshold. Production alerting needs windows and thresholds appropriate to its SLO reporting period and traffic.
- Alertmanager has a receiver without an external notification integration; alerts are observed in its web interface.
- Recovery is manual. No automated rollback or remediation is implemented.
- Integration tests verify the app API. Alert firing, delivery, and resolution are verified through the manual demo sequence; the validation script does not automate those assertions.
- Metrics and failure configuration are held in app memory. Recreating the app resets them, and Prometheus has no configured persistent named data volume.

## References

- [Google SRE Workbook: Implementing SLOs](https://sre.google/workbook/implementing-slos/)
- [Google SRE Workbook: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/)
- [Docker Compose: `up`](https://docs.docker.com/reference/cli/docker/compose/up/)
