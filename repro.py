#!/usr/bin/env python3
"""Install and launch a repro app on a BUSY Bar, then report whether the device rebooted.

Usage:
  python3 repro.py <busybar-ip> <api-key> app.repro.reboot    # expected: REBOOTED
  python3 repro.py <busybar-ip> <api-key> app.repro.control   # expected: no reboot

<api-key> is the HTTP API access key (PIN) or an access token. Python 3 stdlib only.
Reboot is detected by comparing boot_time from GET /api/status/system before and after.
"""
import io
import json
import os
import sys
import tarfile
import time
import urllib.error
import urllib.request

host, key, app_id = sys.argv[1:4]
here = os.path.dirname(os.path.abspath(__file__))


def api(method, path, data=None, ctype="application/json", timeout=10):
    req = urllib.request.Request(f"http://{host}{path}", data=data, method=method,
                                 headers={"X-API-Token": key, "Content-Type": ctype})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def boot_time():
    for _ in range(40):                       # waits up to ~2 min for the device to come back
        try:
            return json.loads(api("GET", "/api/status/system", timeout=3)[1])["boot_time"]
        except Exception:
            time.sleep(3)
    sys.exit("device did not come back")


# package <app_id>/ (the root folder name must equal the manifest id)
buf = io.BytesIO()
with tarfile.open(fileobj=buf, mode="w:gz", format=tarfile.USTAR_FORMAT) as tar:
    tar.add(os.path.join(here, app_id), arcname=app_id)

before = boot_time()
status, text = api("POST", "/api/apps/stage", buf.getvalue(), "application/octet-stream")
print("stage:  ", status, text.strip())
install_key = json.loads(text)["install_key"]
print("install:", *api("POST", f"/api/apps/install?install_key={install_key}"))
print("launch: ", *api("POST", f"/api/apps/launch?app_id={app_id}"))
time.sleep(6)
after = boot_time()
print("RESULT: ", "REBOOTED" if after != before else "no reboot")
print("cleanup:", *api("DELETE", f"/api/apps?app_id={app_id}"))
