#!/usr/bin/env python3
"""Export NDFC fabrics, VRFs, networks, attachments, policies and sync state.

Environment:
  NDFC_URL   e.g. https://10.0.0.40
  NDFC_USER  NDFC username
  NDFC_PASS  NDFC password
"""
import json
import os

import requests
import urllib3

urllib3.disable_warnings()
B = os.environ["NDFC_URL"].rstrip("/")
U = os.environ["NDFC_USER"]
P = os.environ["NDFC_PASS"]
OUT = os.environ.get("OUT", "ndfc")
os.makedirs(OUT, exist_ok=True)

s = requests.Session()
s.verify = False
s.headers.update({"Content-Type": "application/json"})
r = s.post(f"{B}/login", json={"userName": U, "userPasswd": P,
                               "domain": "DefaultAuth", "uiLogin": False}, timeout=30)
tok = (r.json() or {}).get("token") or r.cookies.get("AuthCookie")
s.headers["AuthCookie"] = tok
if r.headers.get("X-Csrf-Token"):
    s.headers["X-Csrf-Token"] = r.headers["X-Csrf-Token"]


def get(path):
    rr = s.get(f"{B}{path}", timeout=120)
    try:
        return rr.json()
    except Exception:
        return {"http": rr.status_code, "text": rr.text[:500]}


def save(name, obj):
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(obj, f, indent=2)


save("fabrics.json", get("/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics"))
for fab in ["DC01", "DC02", "MSD", "EDGE-WAN"]:
    base = f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/top-down/fabrics/{fab}"
    save(f"{fab}_vrfs.json", get(base + "/vrfs"))
    save(f"{fab}_networks.json", get(base + "/networks"))
    save(f"{fab}_vrf_attachments.json", get(base + "/vrfs/attachments"))
    save(f"{fab}_network_attachments.json", get(base + "/networks/attachments"))

for fab, sn, name in [
    ("DC01", "91AJCZEKJI3", "BGW11"), ("DC01", "9BSWEY15TPZ", "LF11"),
    ("DC01", "9C6HJAC4YZD", "LF12"), ("DC01", "9WN8QQVOXNS", "SPN11"),
    ("DC02", "9JPAF7UCYNL", "BGW21"), ("DC02", "9EYZ9KQO8D8", "LF21"),
    ("DC02", "95TVRFRXMX8", "LF22"), ("DC02", "98FQ3BJPX2I", "SPN21"),
]:
    save(f"policies_{name}.json",
         get(f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/policies/switches/{sn}"))
    save(f"pending_{name}.json",
         get(f"/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/{fab}/pendingConfig/{sn}"))
print("done")
