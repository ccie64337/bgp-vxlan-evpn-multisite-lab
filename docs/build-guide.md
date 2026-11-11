# Build Guide

This is the build sequence for the lab.

## 1. EVE-NG images and nodes

| Node | Template / image | Notes |
|---|---|---|
| SPN11, SPN21 | `nxosv9k` 10.6(3) | spines |
| LF11, LF12, LF21, LF22 | `nxosv9k` 10.6(3) | leafs |
| BGW11, BGW21 | `nxosv9k` 10.6(3) | border gateways |
| C8K01 | `c8000v` 17.15.05 | WAN edge |
| FTD01, FTD02 | FTDv | standalone, FMC-managed |
| FMC | FMCv | firewall manager |
| EP11, EP12, EP21, EP22 | `linux-host` | Debian 12 (see `linux-host-image.md`) |

Cabling used in this build:

- SPN11 E1/1–E1/4 → LF11/LF12/BGW11; SPN21 E1/3 → LF22, etc.
- LF11 E1/1 → EP11, LF11 E1/2 → EP12.
- LF22 E1/1 → EP21, LF22 E1/2 → EP22.
- LF12 E1/1 → FTD01 G0/0 (trunk VLAN 10,99), LF12 E1/2 → FTD01 G0/1.
- LF21 E1/1 → FTD02 G0/0 (trunk VLAN 10,99), LF21 E1/2 → FTD02 G0/1.
- BGW11 E1/6 → C8K01 Gi4, BGW21 E1/6 → C8K01 Gi3.
- BGW11 ↔ BGW21 DCI link.

## 2. NDFC fabrics

1. Create `MSD` (MFD), `DC01` (AS 65001), `DC02` (AS 65002), `EDGE-WAN`
   (External, AS 65199).
2. Add DC01/DC02 as members of `MSD`.
3. Onboard SPN11/LF11/LF12/BGW11 into DC01 and SPN21/LF21/LF22/BGW21 into
   DC02.
4. C8K01 is discovered in `EDGE-WAN` but is **not manageable** in NDFC 4.2.1.10
   because the default SNMPv3 credential is MD5 and IOS-XE 17.15 forbids MD5.
   The C8K01 static routes in this build were applied once via console.

## 3. Underlay / overlay

- eBGP underlay per site (AS 65001/65002).
- EVPN overlay with multicast BUM (no ingress replication).
- MSD DCI: eBGP between BGW11/BGW21; SHARED-OUT L3VNI 50010.
- BGW fusion loopbacks: BGW11 `Lo30` 10.255.30.1/32, BGW21 `Lo30`
  10.255.30.2/32, advertised as EVPN Type-5 over the DCI.

## 4. VRFs and networks

Create in the MSD (they propagate to DC01/DC02):

| VRF | VNI | RT |
|---|---|---|
| RED-IN | 50006 | `65001:50101` |
| RED-OUT | 50007 | `65001:50102` |
| BLUE-IN | 50008 | `65002:50201` |
| BLUE-OUT | 50009 | `65002:50202` |
| SHARED-OUT | 50010 | `65000:50300` |
| T1-IN | 50002 | `65000:50099` |

Networks:

| Network | Subnet | VNI | VLAN |
|---|---|---|---|
| RED-NET | 10.11.10.0/24 | 30111 | 2330 |
| BLUE-NET | 10.22.10.0/24 | 30211 | 2340 |
| T1-NET | 10.99.99.0/24 | 30999 | 2399 |

## 5. BGW fusion

NDFC freeform policies (BGW11 `991001`–`991006`, BGW21 `991011`–`991016`):

```
! BGW11
vrf context RED-OUT
  ip route 0.0.0.0/0 10.100.10.2 vrf shared-out
  ip route 10.22.10.0/24 10.255.30.2 vrf shared-out
vrf context shared-out
  ip route 10.11.10.0/24 10.255.20.1 vrf red-out
  ip route 10.99.99.0/24 10.255.20.1 vrf red-out
  ip route 10.99.99.12/32 10.255.20.1 vrf red-out
```

BGW21 mirrors this with `blue-out`, `10.100.20.2`, `10.255.30.1`,
`10.255.21.1`, and `10.99.99.22/32`.

E1/6 is in SHARED-OUT; eBGP to C8K01 AS 65199.

## 6. FTD trunk and FMC

Leaf freeform policies:

- LF12 `991021` / LF21 `991022`: trunk E1/1 (VLAN 10,99), `Vlan10`/`Vlan99`
  SVIs, routed E1/2, and the three dynamic BGP neighbors.
- LF11 `991023` / LF22 `991024`: E1/1 access 2330/2340, E1/2 access 2399,
  and the T1-IN default route.

FTD (FMC):

- `G0/0` trunk with `.10` inside and `.99` T1-IN; `G0/1` outside.
- eBGP AS 65100/65101 to the leaf SVIs.
- Default route via the outside leaf.

## 7. T1-IN stretched VRF

- T1-IN / T1-NET created in the MSD (VNI 50002 / 30999).
- FTD trunk subinterfaces `.99` on both sites.
- Leaf `Vlan99` p2p (10.255.98.4 / 10.255.99.4).
- Leaf T1-IN default to the **local** FTD (`10.255.98.1` / `10.255.99.1`).
- Host `/32`s via EVPN Type-2 (no HMM needed).
- Per-host `/32` steering on C8K01 and the BGW leaks.

## 8. Hosts

Add four `linux-host` nodes and set:

```
EP11 10.11.10.11/24 gw 10.11.10.1
EP12 10.99.99.12/24 gw 10.99.99.1
EP21 10.22.10.21/24 gw 10.22.10.1
EP22 10.99.99.22/24 gw 10.99.99.1
```

Use `systemd-networkd` (see `linux-host-image.md`).

## 9. Validate

Run the matrix in [`validation.md`](validation.md). Expected: all 0% loss,
both FTDs in the inter-site path, and NDFC 8/8 In-Sync.

## NDFC policy reference

The effective (non-`NA`) policies are in `ndfc/effective_policies_*.json`.
Key policies:

| Policy | Device | Purpose |
|---|---|---|
| 991021 | LF12 | FTD01 trunk/SVIs, dynamic eBGP, RED-IN/RED-OUT |
| 991022 | LF21 | FTD02 trunk/SVIs, dynamic eBGP, BLUE-IN/BLUE-OUT |
| 991023 | LF11 | E1/1 2330, E1/2 2399, RED-IN + T1-IN defaults |
| 991024 | LF22 | E1/1 2340, E1/2 2399, BLUE-IN + T1-IN defaults |
| 991001–991006 | BGW11 | E1/6, leaks, C8K01 peer, static redistribution, Lo30 |
| 991011–991016 | BGW21 | E1/6, leaks, C8K01 peer, static redistribution, Lo30 |
