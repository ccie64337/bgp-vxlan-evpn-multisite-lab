# Architecture

## 1. Fabric model

EVE-NG `BGP_VXLAN_EVPN` contains four NDFC fabrics:

| NDFC fabric | Type | Role |
|---|---|---|
| `MSD` | Multi-Site Domain (MFD) | Parent of DC01/DC02 |
| `DC01` | Switch fabric, AS 65001 | Site 1 (SPN11, LF11, LF12, BGW11) |
| `DC02` | Switch fabric, AS 65002 | Site 2 (SPN21, LF21, LF22, BGW21) |
| `EDGE-WAN` | External fabric | C8K01 (AS 65199) |

DC01 and DC02 are members of `MSD`. The Multi-Site DCI is a routed eBGP link
between BGW11 and BGW21.

## 2. VRF sandwich

```
                 DC1                                   DC2
  RED-IN ── FTD01 ── RED-OUT ──┐        ┌── BLUE-OUT ── FTD02 ── BLUE-IN
                               │        │
                            BGW11 ──── BGW21
                               └ SHARED-OUT ┘
```

| VRF | VNI | RT | Where |
|---|---|---|---|
| RED-IN | 50006 | `65001:50101` | LF11, LF12 |
| RED-OUT | 50007 | `65001:50102` | LF11, LF12, BGW11 |
| BLUE-IN | 50008 | `65002:50201` | LF21, LF22 |
| BLUE-OUT | 50009 | `65002:50202` | LF21, LF22, BGW21 |
| SHARED-OUT | 50010 | `65000:50300` | BGW11, BGW21 |
| T1-IN (stretched) | 50002 | `65000:50099` | LF11, LF12, LF21, LF22, BGW11, BGW21 |

The firewalls are the only L3 boundary between the inside and outside VRFs.
BGW11/BGW21 fuse the site outside VRF into the shared VRF with static leaks.

## 3. Inter-site path

```
DC1 host → RED-IN anycast SVI → FTD01 (inside → outside)
  → RED-OUT (LF12) → BGW11 RED-OUT → SHARED-OUT
  → EVPN Type-5 DCI (L3VNI 50010)
  → BGW21 SHARED-OUT → BLUE-OUT → FTD02 (outside → inside)
  → BLUE-IN → DC2 host
```

The return path is the mirror image: it traverses FTD02 then FTD01.

## 4. Firewalls

One **standalone** FTDv per site, managed by FMC (no cluster, no HA, no
session sync).

| Site | FTD | AS | inside | outside | T1-IN |
|---|---|---|---|---|---|
| DC1 | FTD01 | 65100 | 10.255.10.1/29 | 10.255.20.1/29 | 10.255.98.1/29 |
| DC2 | FTD02 | 65101 | 10.255.11.1/29 | 10.255.21.1/29 | 10.255.99.1/29 |

- Leaf↔FTD is **eBGP**; the leaf uses prefix-based dynamic neighbors
  (`neighbor 10.255.x.0/29 remote-as 6510x`), the FTD uses static peers.
- Each FTD has **3 peerings** (inside, outside, T1-IN), one per VRF.
- FTD default route: outside `0.0.0.0/0 → 10.255.20.4 / 10.255.21.4`.
- The leaf T1-IN default points to the **site-local** FTD
  (`0.0.0.0/0 → 10.255.98.1` in DC1, `10.255.99.1` in DC2).

The FTD is a **perimeter/transit** firewall (2-arm role) with an extra T1-IN
transit arm; it is **not** the workload default gateway.

## 5. Stretched T1-IN and host routes

`T1-IN` / `T1-NET` `10.99.99.0/24` is stretched across both sites:

- Anycast gateway `10.99.99.1` on all four leafs
  (`fabric forwarding mode anycast-gateway`).
- EP12 `10.99.99.12` in DC1 (LF11), EP22 `10.99.99.22` in DC2 (LF22).
- The per-host `/32`s are learned as **EVPN Type-2 host routes**
  (VXLAN, `segid 50002`) and are present in the T1-IN VRF BGP table.
- C8K01 and the BGWs use per-host `/32` steering so north-south return traffic
  stays on the correct site:
  - C8K01 `VRF-OUTSIDE`: `10.99.99.12/32 → 10.100.10.1`,
    `10.99.99.22/32 → 10.100.20.1`
  - BGW11 SHARED-OUT → RED-OUT: `10.99.99.0/24` + `10.99.99.12/32`
  - BGW21 SHARED-OUT → BLUE-OUT: `10.99.99.0/24` + `10.99.99.22/32`

HMM is not required: the EVPN Type-2 host routes already provide the `/32`s.
HMM would be used if the peers were not EVPN-aware or if host-route filtering
were needed.

## 6. Anycast gateway

The host gateways are the leaf anycast SVIs, not the firewalls:

```
EP11 10.11.10.1   EP21 10.22.10.1   EP12/EP22 10.99.99.1
```

The same IP and virtual MAC (`2020.0000.00aa`) exist on every leaf with the
SVI. A host ARPs for its gateway, the **local leaf** answers, and the host's
frames are switched by the local leaf — so the gateway is always local and the
north-south traffic uses the local FTD.

## 7. Control plane summary

| Device | AS | Peering |
|---|---|---|
| SPN11 / LF11 / LF12 / BGW11 | 65001 | iBGP DC01, eBGP MSD/DCI to 65002 |
| SPN21 / LF21 / LF22 / BGW21 | 65002 | iBGP DC02, eBGP MSD/DCI to 65001 |
| FTD01 | 65100 | eBGP to LF12 (inside/outside/T1-IN) |
| FTD02 | 65101 | eBGP to LF21 (inside/outside/T1-IN) |
| C8K01 | 65199 | eBGP to BGW11 and BGW21 in SHARED-OUT |

Multicast BUM is used (no ingress replication).
