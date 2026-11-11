# Phase 2 — RED / BLUE / SHARED-OUT Rebuild & Inter-Site Validation

Lab: EVE-NG `BGP_VXLAN_EVPN`
Updated: 2026-11-10

## 1. VRF / network model (NDFC MSD → DC01/DC02)

| Object | VRF | VNI (L3VNI) | RT | Attached to |
|---|---|---|---|---|
| RED-IN | `RED-IN` | 50006 | `65001:50101` | LF11, LF12 |
| RED-OUT | `RED-OUT` | 50007 | `65001:50102` | LF11, LF12, BGW11 |
| BLUE-IN | `BLUE-IN` | 50008 | `65002:50201` | LF21, LF22 |
| BLUE-OUT | `BLUE-OUT` | 50009 | `65002:50202` | LF21, LF22, BGW21 |
| SHARED-OUT | `SHARED-OUT` | 50010 | `65000:50300` | BGW11, BGW21 |
| T1-IN (stretched) | `T1-IN` | 50002 | `65000:50099` | LF11, LF12, LF21, LF22, BGW11, BGW21 |

Host networks (anycast gateway):

| Network | VNI / VLAN | Gateway | VRF |
|---|---|---|---|
| RED-NET | 30111 / 2330 | 10.11.10.1/24 | RED-IN |
| BLUE-NET | 30211 / 2340 | 10.22.10.1/24 | BLUE-IN |
| T1-NET | 30999 / 2399 | 10.99.99.1/24 | T1-IN (stretched) |

> NDFC assigns the L3VNI from the VRF object id (50006-50010); the requested
> `vrfSegmentId` (50101…) is not used. RTs remain the isolation boundary.

Old per-site objects (`APP-A-DC01`, `OUTSIDE-DC01`, `APP-A-DC02`,
`OUTSIDE-DC02`, `WEB-NET-DC01`, `WEB-NET-DC02`) are detached and deleted.

## 2. Firewall integration (standalone FTDv)

| Site | FTD | AS | inside | outside | Leaf |
|---|---|---|---|---|---|
| DC1 | FTD01 | 65100 | 10.255.10.1/29 | 10.255.20.1/29 | LF12 E1/1 / E1/2 |
| DC2 | FTD02 | 65101 | 10.255.11.1/29 | 10.255.21.1/29 | LF21 E1/1 / E1/2 |

- FTDs are standalone (cluster `FTD_CLUSTER` broken); no HA/session sync.
- Leaf↔FTD eBGP uses prefix-based dynamic neighbors
  (`neighbor 10.255.x.0/29 remote-as 6510x`).
- FTD default route: `outside 0.0.0.0/0 → 10.255.20.4 / 10.255.21.4`.
- FTD learns the local host subnet over the inside via BGP (10.11.10.0/24,
  10.22.10.0/24), so return traffic enters the inside.

### BGP AS plan (verified live)

| Device | AS | Peering |
|---|---|---|
| SPN11 / LF11 / LF12 / BGW11 | 65001 | iBGP DC01; eBGP multisite + DCI to 65002 |
| SPN21 / LF21 / LF22 / BGW21 | 65002 | iBGP DC02; eBGP multisite + DCI to 65001 |
| FTD01 | 65100 | eBGP to LF12 (65001) inside + outside |
| FTD02 | 65101 | eBGP to LF21 (65002) inside + outside |
| C8K01 | 65199 | eBGP to BGW11 (65001) + BGW21 (65002) in SHARED-OUT |

C8K01 was moved from 65100 to **65199** so it no longer shares an AS with
FTD01 (they never peer, but the overlap was an operational/AS-path hazard).

## 3. BGW fusion (VRF Sandwich)

Both BGWs are EVPN Multi-Site border gateways (dci-link E1/1, fabric-link
E1/7) with:

- `Ethernet1/6` moved to `SHARED-OUT`:
  - BGW11: 10.100.10.1/30 ↔ C8K01 Gi4 10.100.10.2
  - BGW21: 10.100.20.1/30 ↔ C8K01 Gi3 10.100.20.2
  - eBGP to C8K01 AS **65199** (default + 1.1.1.1/32).
- Fusion loopbacks advertised as EVPN Type-5 over the Multi-Site DCI:
  - BGW11 `Lo30` 10.255.30.1/32 in SHARED-OUT (tag 12345)
  - BGW21 `Lo30` 10.255.30.2/32 in SHARED-OUT (tag 12345)
- Leaks (static inter-VRF, NX-OS `ip route <p> <nh> vrf <vrf>`):
  - BGW11: RED-OUT → SHARED-OUT (default, 10.22.10.0/24 via 10.255.30.2);
    SHARED-OUT → RED-OUT (10.11.10.0/24 via FTD01 outside 10.255.20.1).
  - BGW21: BLUE-OUT → SHARED-OUT (default, 10.11.10.0/24 via 10.255.30.1);
    SHARED-OUT → BLUE-OUT (10.22.10.0/24 via FTD02 outside 10.255.21.1).
  - T1-IN (stretched 10.99.99.0/24) north-south is steered **per host**:
    - BGW11 SHARED-OUT → RED-OUT: `10.99.99.0/24` + `10.99.99.12/32`
    - BGW21 SHARED-OUT → BLUE-OUT: `10.99.99.0/24` + `10.99.99.22/32`
    - C8K01 `VRF-OUTSIDE` return routes: `10.99.99.0/24` and
      `10.99.99.12/32 → 10.100.10.1`, `10.99.99.22/32 → 10.100.20.1`.
    This keeps EP12's north-south on FTD01 and EP22's on FTD02 instead of
    letting the shared /24 pull both to DC1.
- `redistribute static route-map RM-LEAK` + `default-information originate`
  on RED-OUT/BLUE-OUT advertises the remote subnet and default to the leaves.

Resulting inter-site path (symmetric, both firewalls):

```
DC1 host → RED-IN SVI → FTD01 (in→out) → RED-OUT (LF12)
  → BGW11 RED-OUT → SHARED-OUT → EVPN Type-5 DCI (L3VNI 50010)
  → BGW21 SHARED-OUT → BLUE-OUT → FTD02 (out→in) → BLUE-IN → DC2 host
```

Return traffic follows the exact reverse, traversing FTD02 then FTD01.

## 4. Validation performed

| Test | Source → Destination | Result |
|---|---|---|
| DC1 → DC2 | LF12 RED-IN 10.11.10.1 → 10.22.10.1 | **0% loss, TTL 250** |
| DC2 → DC1 | LF21 BLUE-IN 10.22.10.1 → 10.11.10.1 | **0% loss, TTL 250** |
| DC1 → Internet | LF12 RED-IN 10.11.10.1 → 1.1.1.1 | **0% loss, TTL 252** |
| DC2 → Internet | LF21 BLUE-IN 10.22.10.1 → 1.1.1.1 | **0% loss, TTL 252** |
| EP11 → 10.11.10.1 (RED‑IN GW) | 10.11.10.11 | **0%** |
| EP21 → 10.22.10.1 (BLUE‑IN GW) | 10.22.10.21 | **0%** |
| EP12 → 10.99.99.1 (T1‑IN GW) | 10.99.99.12 | **0%** |
| EP22 → 10.99.99.1 (T1‑IN GW) | 10.99.99.22 | **0%** |
| EP11 ↔ EP21 (RED‑IN ↔ BLUE‑IN) | 10.11.10.11 ↔ 10.22.10.21 | **0% both directions** |
| EP12 ↔ EP22 (T1‑IN stretched) | 10.99.99.12 ↔ 10.99.99.22 | **0% both directions** |
| EP11 → 1.1.1.1 | 10.11.10.11 | **0% (FTD01 only)** |
| EP21 → 1.1.1.1 | 10.22.10.21 | **0% (FTD02 only)** |
| EP12 → 1.1.1.1 | 10.99.99.12 | **0% (FTD01 only)** |
| EP22 → 1.1.1.1 | 10.99.99.22 | **0% (FTD02 only)** |

Stateful proof (live ICMP stream EP11 ↔ EP21):

```
FTD01: ICMP inside  10.11.10.11:444 outside 10.22.10.21:0, bytes 1232
FTD02: ICMP outside 10.11.10.11:444 inside  10.22.10.21:0, bytes 1960
```

The inter‑site flow therefore enters FTD01 on `inside` and exits `outside`,
then enters FTD02 on `outside` and exits `inside`; the reverse direction is
the mirror image. T1‑IN north‑south is symmetric per host after the
`10.99.99.12/.22` /32 steering.

Endpoints: EP11 10.11.10.11, EP12 10.99.99.12, EP21 10.22.10.21,
EP22 10.99.99.22 (all /24). EVE‑NG console ports are dynamic.

### Host-route / AS-path prepend validation (temporary test)

Applied `route-map RM-PREPEND` on LF12 RED-OUT → FTD01 outside
(`deny` local 10.11.10.0/24, `match` remote prefix, `set as-path prepend
65001 65001 65001 65001`, permit rest), then reverted.

| Check | Result |
|---|---|
| FTD01 AS-path for 10.22.10.0/24 during test | `65001 65001 65001 65001 65001` |
| Inter-site traffic during test | **0% loss** |
| After revert | AS-path `65001`, `rm-ftd-out out` restored, **0% loss** |

Key finding: `match as-path _65002_` did **not** match. The EVPN Type‑5
prefix arrives at the leaf with an **empty AS-path** (the Multi‑Site
rewrite/origination does not preserve the remote AS in the leaf’s VRF BGP
table), so in this design the remote prefix must be matched by
**prefix-list** (or an EVPN route tag/community), while `set as-path
prepend` still works normally.

The full stretched-subnet host-route test is now live: T1-IN has an FTD
trunk subinterface (`G0/0.99`), HMM advertises the host /32s, and the /32s
steer north-south per host (see the T1-IN section below).

### T1-IN stretched inside VRF (live)

Built and live (baseline traffic unaffected):

| Object | Value | Attached |
|---|---|---|
| VRF `T1-IN` | VNI 50002, RT `65000:50099`, VRF VLAN 2031 | LF11, LF12, LF21, LF22, BGW11, BGW21 |
| Network `T1-NET` | 10.99.99.0/24, VNI 30999, VLAN 2399, GW 10.99.99.1 | LF11, LF12, LF21, LF22 |

- `show ip route vrf t1-in` on all four leafs shows 10.99.99.0/24 attached.
- The VRF is stretched across the MSD (same RT/VNI on both sites).

Applied (previously "pending"):

1. **FTD trunk cutover** — **DONE**. FTD01/02 `G0/0` are now trunks with
   `G0/0.10` (existing inside p2p) and `G0/0.99` (T1-IN p2p
   10.255.98.0/29 DC1 / 10.255.99.0/29 DC2). Leaf `E1/1` is
   `switchport mode trunk` (VLAN 10,99) with `Vlan10`/`Vlan99` SVIs.
   All three eBGP sessions per FTD are up (inside, outside, T1-IN).
2. **T1-IN default route** — **DONE** on LF11/LF12 (10.255.98.1) and
   LF22/LF21 (10.255.99.1).
3. **BGW fusion** — **DONE**. SHARED-OUT leak for 10.99.99.0/24 and the
   per-host /32s (10.99.99.12 → RED-OUT/FTD01, 10.99.99.22 →
   BLUE-OUT/FTD02) on BGW11/BGW21; C8K01 has matching /24 + /32 routes.
   The old `.10/.20` entries were replaced via NDFC policies 991003/991013
   (deployed) and the C8K01 `VRF-OUTSIDE` routes were updated + saved.
4. **HMM** — **DONE**. `feature hmm` + `redistribute hmm` in T1-IN on
   LF12/LF21 with a /32 route-map. Both FTDs learn the host /32s
   dynamically (`show route 10.99.99.12` on FTD01 via 10.255.98.4;
   `10.99.99.22` on FTD02 via 10.255.99.4).
5. **Endpoints** — **DONE**. EP12 = 10.99.99.12/24, EP22 =
   10.99.99.22/24, gw 10.99.99.1. RED-NET/BLUE-NET now host EP11/EP21
   (10.11.10.11 / 10.22.10.21).

T1-IN validation (all 0% loss):

| Test | Result |
|---|---|
| EP12 → 10.99.99.1 (anycast GW) | 0% |
| EP22 → 10.99.99.1 (anycast GW) | 0% |
| EP12 ↔ EP22 (stretched L2 over DCI) | 0% |
| EP12 → 1.1.1.1 (north-south via FTD01) | 0% |
| EP22 → 1.1.1.1 (north-south via FTD02) | 0% |

The DC2 north-south flow was asymmetric until the per-host /32 steering
was added (C8K01 sent the /24 to DC1); with `.22/32` → 10.100.20.1 it is
symmetric and passes. EP12 and EP22 are the first hosts on the new
Linux image (see `linux-host-image.md`).

FMC gotchas hit during the cutover: subinterface `ifname` must not
duplicate the parent's nameif, and the BGP object rejects the deprecated
`maximumPaths` field. NDFC gotchas: stale `int_trunk_host` policies on
E1/1 (LF11/LF21) and E1/2 (LF21) blocked the freeform deploy until
deleted; VLANs 10/99 must be explicitly created for the SVIs to come up;
a stale `no interface loopback100` line blocked LF11/LF22 until removed.

EVPN / BGP state:

| Check | Detail | State |
|---|---|---|
| BGW11 EVPN | SHARED-OUT 10.255.30.2/32 via BGW21 VTEP | learned (segid 50010) |
| BGW21 EVPN | SHARED-OUT 10.255.30.1/32 via BGW11 VTEP | learned (segid 50010) |
| Leaf EVPN | LF12 RED-OUT 10.22.10.0/24 via BGW11 | learned (segid 50007) |
| Leaf EVPN | LF21 BLUE-OUT 10.11.10.0/24 via BGW21 | learned (segid 50009) |
| C8K01 BGP | 10.100.10.1 / 10.100.20.1 | Established |

SVI-sourced pings must use the leaf that hosts the site FTD (LF12/LF21),
because both leafs share the anycast gateway IP and the reply is delivered
locally by the leaf that owns the FTD.

## 5. Open items / blockers

1. **Docker → Linux endpoints** — replaced. Four Debian 12 hosts
   (`linux-host` image) now sit on the leafs:
   EP11 10.11.10.11 (RED‑IN), EP21 10.22.10.21 (BLUE‑IN),
   EP12 10.99.99.12 and EP22 10.99.99.22 (T1‑IN). All host tests pass.
   - **EVE‑NG tenant caveat**: the API session runs in tenant 0 and the GUI
     in tenant 1, so a node started from both gets two QEMU instances with
     separate console ports and tap sets. The GUI telnet showed the baked
     `10.99.99.10` on every host until the tenant‑0 duplicates were killed
     and the IPs were set on the tenant‑1 consoles. Some host taps also had
     to be moved onto the leaf E1/1 bridge (`brctl delif/addif`). A clean
     lab reload (Lab → Reload) would remove the duplicates; it has not been
     run yet.
2. **C8K01 north-south return** — resolved. C8K01 is **AS 65199** and has
   `10.11.10.0/24 → 10.100.10.1`, `10.22.10.0/24 → 10.100.20.1`,
   `10.99.99.0/24 → 10.100.10.1`, `10.99.99.12/32 → 10.100.10.1`,
   `10.99.99.22/32 → 10.100.20.1` in `VRF-OUTSIDE` (saved with
   `write memory`). The BGW `SHARED-OUT` neighbors were updated to
   `remote-as 65199` via NDFC. All four hosts reach `1.1.1.1` at 0% loss.
   - NDFC onboarding of C8K01 remains blocked: the device is discovered but
     `managable: false` because NDFC's default SNMPv3 credential is **MD5**
     and IOS-XE 17.15 forbids MD5 SNMPv3 users. A one-time CLI session on
     C8K01 was approved and used for the AS change + static routes; all BGW
     changes were done through NDFC.
3. **Test loopbacks** could not be applied through NDFC freeform
   (`ip address` on `loopback100` in a VRF is silently dropped by the
   config generator); SVI-sourced pings were used instead.
4. **ECMP `maximum-paths 64`** remains a symmetry risk (Test 08).
5. `export-gateway-ip` / Local-AS still not configured (Phase 1 gaps).

## 6. NDFC policy layout (effective `switch_freeform_config`)

| Policy | Device | Purpose |
|---|---|---|
| 991021 | LF12 | FTD01 p2p, dynamic eBGP, RED-IN/RED-OUT |
| 991022 | LF21 | FTD02 p2p, dynamic eBGP, BLUE-IN/BLUE-OUT |
| 991023 | LF11 | access VLAN 2330 + RED-IN default |
| 991024 | LF22 | access VLAN 2340 + BLUE-IN default |
| 991001/2/3/4/5/6 | BGW11 | E1/6, leaks, C8K01 peer, static redistribution, Lo30 |
| 991011/2/3/4/5/6 | BGW21 | E1/6, leaks, C8K01 peer, static redistribution, Lo30 |
| 991003 / 991013 | BGW11 / BGW21 | SHARED-OUT → RED-OUT/BLUE-OUT leaks; hold the `10.99.99.12/.22` per-host /32s |
| 991023 / 991024 | LF11 / LF22 | E1/1 2330/2340, E1/2 2399 (T1-NET), RED-IN/BLUE-IN + T1-IN defaults |

Legacy `switch_freeform` policies 990001-990006 were deleted; NDFC
auto-generates a `switch_freeform_config` copy, which is the effective one.

## 7. NDFC cleanup & sync (2026-11-10)

Both site fabrics are **fully in sync** (8/8 switches: BGW11, LF11, LF12,
SPN11, BGW21, LF21, LF22, SPN21).

Removed as leftovers from the previous (cluster/service-insertion) deployment:

| Object | Type | Reason |
|---|---|---|
| `APP-A-VRF` (50001) | VRF | `NA`, 0 attachments |
| `VRF-OUTSIDE` (50000) | VRF | `NA`, 0 attachments |
| `WEB-NET` (30000) | Network | `NA`, 0 attachments |
| `FTD-OUTSIDE` (3010) | Service network | `NA`, 0 attachments |
| `FTD-PERIMETER-FUNC-V2` | L4‑L7 service function | no service insertion |
| `FTD-CLUSTER-MSD-V2` | L4‑L7 service cluster | no service insertion |
| WEB‑NET service networks | Service network refs | MSD/DC01/DC02 |
| `POLICY-534720` | `int_trunk_host` LF12 E1/2 | stale VLAN 3010 trunk |
| `POLICY-993001/2` | HMM freeform | redundant (EVPN host routes already give the /32s) |

Also cleaned via NDFC:

- Removed the stale `switchport trunk native vlan 2300` from LF12 E1/1
  (encoded in policy 991021 and deployed).
- Normalised the BGW leak policy VRF names to lowercase (`red-out`,
  `blue-out`, `shared-out`) to match NX‑OS `show running-config` rendering;
  this cleared the last BGW compliance delta.
- Deleted the auto‑generated `int_trunk_host` defaults on the FTD leaf
  E1/1/E1/2 that conflicted with the access/routed config.

The `/32` host routes are provided by **EVPN Type‑2 host routes**
(`segid 50002`), so HMM redistribution is not required for the current
T1‑IN steering. Data path after the cleanup: all eight host tests 0%
(EP11↔EP21, EP12↔EP22, all four hosts → 1.1.1.1).

NDFC deploy quirk observed: `config-deploy` can return
"Configuration deployment completed" without applying the delta when a
stale `int_trunk_host`/freeform policy is present; deleting the stale
policy and redeploying is what actually clears the compliance state.
Deploys also flap the FTD eBGP sessions briefly, so allow a minute for
convergence before judging the data path.
