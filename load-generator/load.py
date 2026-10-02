import os
import time

import requests


target_url = os.getenv("TARGET_URL", "http://app:8000/work")
interval_seconds = float(os.getenv("REQUEST_INTERVAL_SECONDS", "0.1"))

while True:
    try:
        response = requests.get(target_url, timeout=2)
        print(f"status={response.status_code}", flush=True)
    except requests.RequestException as error:
        print(f"request_failed={error}", flush=True)

    time.sleep(interval_seconds)