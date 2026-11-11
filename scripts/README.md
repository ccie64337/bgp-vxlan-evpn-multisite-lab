# Scripts

Helper scripts used to export the lab state. All credentials come from
environment variables — nothing is hardcoded.

## `export_ndfc.py`

```bash
export NDFC_URL=https://10.0.0.40
export NDFC_USER=admin
export NDFC_PASS='<password>'
python3 export_ndfc.py
```

Writes `ndfc/fabrics.json`, `ndfc/<fabric>_vrfs.json`,
`ndfc/<fabric>_networks.json`, `ndfc/<fabric>_*_attachments.json`,
`ndfc/policies_<switch>.json`, and `ndfc/pending_<switch>.json`.
The committed repo keeps the filtered `ndfc/effective_policies_<switch>.json`.

## `export_configs.py`

```bash
export DEVICE_USER=admin
export DEVICE_PASS='<password>'
python3 export_configs.py
```

Pulls `show running-config` from the NX-OS leafs/BGWs/spines, C8K01, and the
FTDs, then redacts passwords, secrets, SNMP communities, and keys.

## `screenshot_topology.py`

```bash
export EVE_URL=https://192.168.100.33
export EVE_USER=admin
export EVE_PASS='<password>'
export OUT=topology/topology.png
python3 screenshot_topology.py
```

Logs into EVE-NG, opens the last lab, clicks **auto zoom to fit all elements**,
and saves a clean PNG.

> EVE-NG also has a built-in **More actions → Topology Screenshot** option in
> the lab UI, which produces a clean client-side capture in a normal browser.
