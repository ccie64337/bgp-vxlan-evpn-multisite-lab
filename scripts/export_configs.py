#!/usr/bin/env python3
"""Export running-configs from NX-OS / IOS-XE / FTD and redact secrets.

Environment:
  DEVICE_USER  SSH username
  DEVICE_PASS  SSH password
"""
import os
import re

import pexpect

USER = os.environ.get("DEVICE_USER", "admin")
PASS = os.environ.get("DEVICE_PASS", "")
OUT = os.environ.get("OUT", "configs")
os.makedirs(OUT, exist_ok=True)

# (name, ip, kind)  kind: nxos | iosxe | ftd
DEVICES = [
    ("SPN11", "10.0.0.10", "nxos"), ("SPN21", "10.0.0.20", "nxos"),
    ("LF11", "10.0.0.11", "nxos"), ("LF12", "10.0.0.12", "nxos"),
    ("LF21", "10.0.0.21", "nxos"), ("LF22", "10.0.0.22", "nxos"),
    ("BGW11", "10.0.0.13", "nxos"), ("BGW21", "10.0.0.23", "nxos"),
    ("C8K01", "10.0.0.60", "iosxe"),
    ("FTD01", "10.0.0.51", "ftd"), ("FTD02", "10.0.0.52", "ftd"),
]


def redact(s):
    s = re.sub(r'(?im)^(\s*(?:enable\s+)?password\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*(?:enable\s+)?(?:secret|passwd)\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*snmp-server\s+community\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*key-string\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*key\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*username\s+\S+\s+password\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    s = re.sub(r'(?im)^(\s*pre-shared-key\s+)(\S+)(.*)$', r'\1<REDACTED>', s)
    return s


def grab(ip, kind):
    prompt = r">\s*$" if kind == "ftd" else r"[#>]\s*$"
    c = pexpect.spawn(
        f"ssh -tt -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "
        f"-o ConnectTimeout=15 -o PreferredAuthentications=password -o PubkeyAuthentication=no {USER}@{ip}",
        encoding="utf-8", timeout=60)
    try:
        if c.expect([r"[Pp]assword:", pexpect.TIMEOUT, pexpect.EOF]) == 0:
            c.sendline(PASS)
        c.expect([prompt, pexpect.TIMEOUT], timeout=40)
        if kind != "ftd":
            c.sendline("terminal length 0")
            c.expect([prompt, pexpect.TIMEOUT], timeout=20)
        else:
            c.sendline("")
            c.expect([prompt, pexpect.TIMEOUT], timeout=20)
        c.sendline("show running-config")
        buf = ""
        while True:
            j = c.expect([r"--More--", prompt, pexpect.TIMEOUT], timeout=60)
            buf += c.before
            if j == 0:
                c.send(" ")
                continue
            break
        return buf
    finally:
        c.close(force=True)


for name, ip, kind in DEVICES:
    d = os.path.join(OUT, {"nxos": "nxos", "iosxe": "c8k01", "ftd": "ftd"}[kind])
    os.makedirs(d, exist_ok=True)
    try:
        open(os.path.join(d, f"{name}.cfg"), "w").write(redact(grab(ip, kind)))
        print("saved", name)
    except Exception as e:
        print("ERR", name, e)
