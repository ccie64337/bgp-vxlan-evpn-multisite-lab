# Phase 1 — Software Compatibility & Feature Validation

Lab: EVE-NG `BGP_VXLAN_EVPN` (id `eb8bb80e-d367-4ef6-9524-58e4027990e6`)
Validated on: 2026-11-09

## 1. Image inventory (EVE-NG)

| Role | Node(s) | Template | Image | RAM | vCPU | NICs |
|---|---|---|---|---|---|---|
| Spine | SPN11, SPN21 | nxosv9k | `nxosv9k-10.6.3.F` | 16 GB | 4 | 8 |
| Service Leaf | LF11, LF12, LF21, LF22 | nxosv9k | `nxosv9k-10.6.3.F` | 16 GB (LF21 8 GB) | 4 (LF21 2) | 8 |
| BGW | BGW11, BGW21 | nxosv9k | `nxosv9k-10.6.3.F` | 16 GB | 4 | 8 |
| FTDv | FTD01, FTD02 | ftd7 | `ftd7-FTD-7.7.0-89` | 16 GB | 8 / 4 | 6 |
| FMC | FMC | fmc7 | `fmc7-7.7.0-91` | 28 GB | 4 | 1 |
| Edge router | C8K01 | c8000v | `c8000v-17.15.05` | 8 GB | 4 | 4 |
| Endpoint | EP11, EP21, EP31 | docker / eve-gui-server | `eve-gui-server:latest` | 1 GB | 1 | 1 |

## 2. Running software versions

| Component | Version |
|---|---|
| NX-OS (N9Kv) | **10.6(3)** (`nxos64-cs.10.6.3.F.bin`) |
| FTDv | **7.7.0 (Build 89)** |
| FMC | **7.7.0 (Build 91)** |
| C8000V | 17.15.05 |

## 3. Feature validation against the selected images

| Capability | Status | Evidence |
|---|---|---|
| EVPN Multi-Site BGW | ✅ | `evpn multisite border-gateway 1`; `show nve multisite fabric-links` = E1/7 Up; `dci-links` = E1/1 Up |
| EVPN Type-5 | ✅ | `show bgp l2vpn evpn summary` — Type-5 = 4 from iBGP peer |
| VLAN-based L3VNI | ✅ | `show nve vni` — 50002 (app-a-dc01), 50003 (outside-dc01) L3 |
| Anycast Gateway | ✅ | `interface Vlan2310` → `fabric forwarding mode anycast-gateway` |
| VXLAN NVE | ✅ | `feature nve` enabled; `nve1` up |
| BGP + EVPN control plane | ✅ | `feature bgp`; EVPN neighbors Established (iBGP 65001, eBGP 65002 DCI) |
| BGP Route Maps / Prefix Lists | ✅ | `route-map`, `ip prefix-list`, `ip as-path access-list` present |
| BGP AS-Path manipulation | ✅ | `ip as-path access-list`, route-map `match as-path` present |
| BGP Local-AS | ⚠️ not configured | NX-OS 10.6 supports `neighbor <ip> local-as`; must be added per design |
| Local Preference | ✅ (supported) | standard NX-OS; not yet used |
| MED | ✅ (supported) | standard NX-OS; not yet used |
| BGP Communities | ✅ (supported) | `send-community` in EVPN config |
| `export-gateway-ip` | ⚠️ not configured | per-VRF knob; must be added on BGWs |
| ECMP / maximum-paths | ✅ | `maximum-paths 64` / `maximum-paths ibgp 64` (note: ECMP is a symmetry risk — Test 08) |
| BFD | ⚠️ disabled | `feature bfd` = disabled; can be enabled |
| Ingress Replication | ❌ currently **multicast** | L2 VNI 30101 uses `mcast-group 239.1.1.0`; must switch to `ingress-replication` per spec |
| FTDv routed mode | ✅ | FTD 7.7.0 standalone (cluster broken) |
| FTDv eBGP | ✅ | BGP sessions up (FTD01 65100↔LF12, FTD02 65101↔LF21) |
| FTDv stateful inspection | ✅ | `show conn`, `show asp drop` available |
| Linux endpoints (iperf3/tcpdump/ss) | ❌ | current endpoints are `eve-gui-server` docker; need a real Linux VM image |

## 4. Gaps to close before Phase 2

1. **Ingress Replication** — replace multicast `mcast-group` on L2 VNIs with `ingress-replication` (or `nve ... ingress-replication protocol bgp`).
2. **Linux endpoints** — the spec needs Linux VMs (iperf3/tcpdump/ss/ss). Current docker GUI servers are insufficient; need a Linux image in EVE-NG (e.g., ubuntu/debian) or use the docker node with a full Linux image.
3. **`export-gateway-ip`** on BGWs (per-VRF) for Type-5 origin.
4. **Local-AS** — decide inside/outside local-as values for the FTD/leaf eBGP.
5. **VRF model mapping** — the spec uses `RED-IN/RED-OUT/BLUE-IN/BLUE-OUT/SHARED-OUT`. Current per-site VRFs are `APP-A-DC01/OUTSIDE-DC01`, `APP-A-DC02/OUTSIDE-DC02`. Need to decide rename vs map.
6. **ECMP** — reduce/control maximum-paths to avoid unintended asymmetry (Test 08).

## 5. Topology note

Current lab is a superset of the target: 2 spines, 4 service leaves (2 per site), 2 BGWs, 2 standalone FTDs. The target per-site roles (Spine, Service Leaf, BGW, FTDv) are all present; the extra leaves can serve as additional service leaves or be removed for a minimal footprint.

## 6. Phase 2 entry criteria

- Confirm the VRF model (RED/BLUE/SHARED-OUT vs current APP-A-DCxx).
- Confirm the endpoint image (Linux VM).
- Confirm ingress-replication vs multicast for BUM.
- Then deploy the local underlay + EVPN per site (Phase 2).
