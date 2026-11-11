# NDFC export

Read-only exports from NDFC 4.2.1.10 (`https://10.0.0.40`) for the
`MSD`, `DC01`, `DC02`, and `EDGE-WAN` fabrics.

| File | Meaning |
|---|---|
| `fabrics.json` | Fabric inventory (name, type, ASN) |
| `<fabric>_vrfs.json` | VRFs defined in that fabric |
| `<fabric>_networks.json` | Networks defined in that fabric |
| `<fabric>_vrf_attachments.json` | Per-switch VRF attachment records |
| `<fabric>_network_attachments.json` | Per-switch network attachment records |
| `effective_policies_<switch>.json` | Effective (non-`NA`) policies for the switch |
| `summary.json` | Counts and sync summary |

## Sync state

All eight switches are **in sync**:

```
DC01: BGW11, LF11, LF12, SPN11
DC02: BGW21, LF21, LF22, SPN21
```

`summary.json` reports `pending_lines: 0` for every switch. The raw
`/pendingConfig/{serial}` exports were empty (`{"pendingConfig": []}`) and are
not committed; run the export script if you want them again.

## Status values

| Value | Meaning |
|---|---|
| `DEPLOYED` | Attached to this fabric and deployed |
| `NA` | Not applicable here — not attached to this fabric, or an auto-generated default policy for an unused port |
| *no `status` key* | Effective freeform policy (deployed) |

Examples:

- `DC01_vrfs.json`: `BLUE-IN` / `BLUE-OUT` are `NA` in DC01 because they belong
  to DC02; `RED-IN` / `RED-OUT` are `DEPLOYED`.
- `DC01_networks.json`: `BLUE-NET` is `NA` in DC01 for the same reason.
- `effective_policies_*.json`: only the effective policies (6–14 per switch).
  The full dump contains hundreds of `NA` per-port defaults
  (`int_trunk_host` / `int_routed_host`); those are normal and were omitted to
  keep the repo small.

## Regenerate

```bash
export NDFC_URL=https://10.0.0.40
export NDFC_USER=admin
export NDFC_PASS='<password>'
python3 ../scripts/export_ndfc.py
```

The script writes the full `policies_<switch>.json` and
`pending_<switch>.json`; keep only the non-`NA` policies for the committed
`effective_policies_<switch>.json`.
