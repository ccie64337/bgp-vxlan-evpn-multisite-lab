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
| `policies_<switch>.json` | All policies for the switch (auto-generated + freeform) |
| `pending_<switch>.json` | Pending-config delta for the switch |
| `summary.json` | Counts and sync summary |

## Sync state

`pending_<switch>.json` is named after the NDFC endpoint
(`/pendingConfig/{serial}`), **not** a state. All eight files contain:

```json
{ "pendingConfig": [] }
```

`summary.json` reports `pending_lines: 0` for every switch, i.e. **all switches
are in sync** (DC01: BGW11, LF11, LF12, SPN11; DC02: BGW21, LF21, LF22, SPN21).

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
- `policies_*.json`: most `NA` entries are the per-port default
  `int_trunk_host` / `int_routed_host` policies. They are normal and harmless.

## Regenerate

```bash
export NDFC_URL=https://10.0.0.40
export NDFC_USER=admin
export NDFC_PASS='<password>'
python3 ../scripts/export_ndfc.py
```
