# C8000v Edge Router — NDFC External VXLAN Rebuild (Option A)

## Objective
Deploy C8K01 as an NDFC-managed edge router for the DC01/DC02 MSD VXLAN EVPN
fabric, with:
- L2 extension of the cloud segment (VNI 30000 / 192.168.10.0/24)
- EVPN/VXLAN peering with BGW11/BGW21
- tenant VRF `app-a-vrf` with L3VNI 50001 (routed multi-tenancy)

## Correct NDFC model (key correction)
The original `EDGE-WAN` fabric was `External_Fabric` with
`unifiedNDFabricType=externalConnectivity` (VRF-Lite/custom-network model).
That model cannot extend VXLAN/EVPN to an IOS-XE edge router.

The correct model is:

| Item | Value |
|---|---|
| Fabric template | `External_Fabric` |
| `unifiedNDFabricType` | `vxlanExternal` |
| `EXT_FABRIC_TYPE` (label) | `Multi-Site Interconnect Network` |
| Fabric name | `EDGE-WAN-VX` |
| MSD association | member of `MSD` (`POST /control/fabrics/msdAdd`) |
| Device role | `edge router` |
| Platform discovery | `CSR1000V` (C8000v is accepted by the `csr_*` templates) |

`externalConnectivity` and `vxlanExternal` are mutually exclusive fabric
models; the type cannot be changed in place on a populated fabric.

## Build sequence used

1. Back up C8K01/BGW11/BGW21 running-config and NDFC state.
2. Create `EDGE-WAN-VX`:
   - `POST /rest/control/fabrics/EDGE-WAN-VX/External_Fabric`
   - nvPairs: `BGP_AS=65100`, `unifiedNDFabricType=vxlanExternal`,
     `EXT_FABRIC_TYPE=Multi-Site Interconnect Network`, `IS_READ_ONLY=false`
   - `POST /rest/control/fabrics/msdAdd`
     `{"destFabric":"MSD","sourceFabric":"EDGE-WAN-VX"}`
3. Remove C8K01 from the old `EDGE-WAN` fabric and discover it in
   `EDGE-WAN-VX` with `platform=CSR1000V`, role `edge router`.
4. Clean the C8K01 manual overlay/VRF/IFC config, keeping management/SSH/SNMP.
5. NDFC policies on C8K01:
   - `csr_int_loopback` — Loopback0 `10.200.0.1/32` (VTEP/router-id)
   - `csr_int_nve` — `nve1`, `source-interface Loopback0`
6. NDFC Inter-Fabric Links (IFCs):
   - underlay: `csr_ext_multisite_underlay_setup`
     - BGW11 Eth1/6 ↔ C8K01 Gi4, `10.200.10.1/30` ↔ `10.200.10.2`
     - BGW21 Eth1/6 ↔ C8K01 Gi3, `10.200.20.1/30` ↔ `10.200.20.2`
   - overlay: `csr_ext_evpn_multisite_overlay_setup`
     - BGW11 loopback1 (`10.1.1.1`) ↔ C8K01 Loopback0 (`10.200.0.1`)
     - BGW21 loopback1 (`10.2.1.1`) ↔ C8K01 Loopback0 (`10.200.0.1`)
7. NDFC device policies:
   - `csr_vrf_evpn` — `app-a-vrf`, RD `65100:50001`, L3VNI 50001,
     BD 2001, BDI 2001, `advertise l2vpn evpn`
   - `ios_xe_switch_freeform` — L2VNI 30000 / BD 2300 / Gi2 service
     instance 2300, explicit L2VNI RTs, second VRF RT `65002:50001`,
     underlay loopback advertisement, multicast/PIM.

## Current verified state

C8K01:
- L2VNI 30000: **Up** (BD 2300, ingress-replication)
- L3VNI 50001: **Up** (BD 2001, VRF `app-a-vrf`)
- EVPN neighbors 10.1.1.1 / 10.2.1.1: **Up**
- VRF `app-a-vrf` imports Type-5 `192.168.10.0/24` (binding label 0x3000001)
- Underlay eBGP neighbors 10.200.10.1 / 10.200.20.1: **Up**
- BGW11/BGW21 see C8K01 EVPN neighbor 10.200.0.1: **Up**

Data plane:
- EP31 (cloud, 192.168.10.13) ↔ EP01 (192.168.10.11): **0% loss** (~12–17 ms)
- EP31 ↔ EP21 (192.168.10.12): **0% loss** (~12–14 ms)
- EP01 ↔ EP31: **0% loss** (~11–13 ms)
- EP21 ↔ EP31: **0% loss** (~11–12 ms)
- C8K01 `ping vrf app-a-vrf 192.168.10.11 source 10.255.255.1`: **success**
  (L3VNI routed path works)

## Recommended gateway design (implemented)

C8K01 now acts as the cloud segment's default gateway on a dedicated tenant
L2VNI/BD:

| Item | Value |
|---|---|
| L2VNI | 31000 |
| BD | 2400 |
| BDI | `BDI2400` in `app-a-vrf` |
| Gateway IP | `192.168.20.1/24` |
| EP31 | moved to `192.168.20.13/24`, gateway `192.168.20.1` |
| DC reachability | via L3VNI 50001 (Type-5) |

The C8K01 L2VNI 31000 is **Up** (BD 2400, `cfg vrf app-a-vrf`, Core IRB
L3VNI 50001). The original L2VNI 30000 remains configured and Up, but the
Gi2 service instance is now on BD 2400. To return to the L2-extension test,
move the Gi2 service instance back to BD 2300.

Verified after the change:
- EP31 → `192.168.20.1` (C8K BDI): **reachable**
- EP31 → `192.168.10.1` (DC leaf anycast SVI): **0% loss**
- EP31 → EP01 `192.168.10.11` (DC01): **0% loss** (~17–22 ms)
- EP31 → EP21 `192.168.10.12` (DC02): **fails**

## Residual: DC02 Type-5 RT

The C8K01 Type-5 `192.168.20.0/24` is advertised with **RT 65001:50001 only**,
so BGW11/DC01 imports it but BGW21/DC02 (which imports `65002:50001`) does not.
`BGW21` and `LF22` have no route for `192.168.20.0/24` or `.13`.

Cause: the `csr_vrf_evpn` template exports a single `stitching` RT
(`65001:50001`). The extra `route-target export 65002:50001` is present in the
VRF but is not included in the EVPN Type-5 extcommunity.

Fix: replace the `csr_vrf_evpn` VRF policy with the NDFC
`Default_VRF_Extension_Universal` template and set:

```
routeTargetExportEvpn = 65001:50001,65002:50001
routeTargetImportEvpn = 65001:50001,65002:50001
```

That template's IOS-XE branch generates the VRF/L3VNI/BDI/NVE/BGP VRF AF and
includes the explicit EVPN RTs in the Type-5. The `csr_vrf_evpn` template does
not expose `routeTargetExportEvpn`, which is why DC02 is missing the route.

## Rollback
Backups:
- `/tmp/opencode/backup_20261107/C8K01.cfg`
- `/tmp/opencode/backup_20261107/BGW11.cfg`
- `/tmp/opencode/backup_20261107/BGW21.cfg`
- `/tmp/opencode/backup_20261107/ndfc_state.txt`

Old `EDGE-WAN` fabric remains standalone (device removed) as a rollback
artifact; it can be deleted once the new build is accepted.
