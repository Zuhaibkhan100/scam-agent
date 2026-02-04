import os
import time
from datetime import datetime

import requests

url = os.getenv("WARM_URL", "https://scam-agent.onrender.com/health")
interval = int(os.getenv("WARM_INTERVAL_SECONDS", "300"))
timeout = float(os.getenv("WARM_TIMEOUT_SECONDS", "5"))

print(f"Warming {url} every {interval}s (timeout {timeout}s)")

while True:
    ts = datetime.utcnow().isoformat() + "Z"
    try:
        resp = requests.get(url, timeout=timeout)
        body = (resp.text or "")[:200]
        print(f"{ts} {resp.status_code} {body}")
    except Exception as e:
        print(f"{ts} error {e}")
    time.sleep(interval)
