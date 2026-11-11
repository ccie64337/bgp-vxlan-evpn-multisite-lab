# Validation

All tests were run live on the lab. Every flow is **0% loss**.

## Host matrix

| Source | Destination | Result |
|---|---|---|
| EP11 (10.11.10.11) | 10.11.10.1 (RED-IN GW) | 0% |
| EP21 (10.22.10.21) | 10.22.10.1 (BLUE-IN GW) | 0% |
| EP12 (10.99.99.12) | 10.99.99.1 (T1-IN GW) | 0% |
| EP22 (10.99.99.22) | 10.99.99.1 (T1-IN GW) | 0% |
| EP11 ↔ EP21 | inter-site | 0% both ways |
| EP12 ↔ EP22 | stretched T1-IN | 0% both ways |
| EP11 → 1.1.1.1 | north-south | 0% (FTD01 only) |
| EP21 → 1.1.1.1 | north-south | 0% (FTD02 only) |
| EP12 → 1.1.1.1 | north-south | 0% (FTD01 only) |
| EP22 → 1.1.1.1 | north-south | 0% (FTD02 only) |

## Both firewalls in the inter-site path

Live ICMP stream EP11 ↔ EP21:

```
FTD01: ICMP inside  10.11.10.11:444 outside 10.22.10.21:0
FTD02: ICMP outside 10.11.10.11:444 inside  10.22.10.21:0
```

The forward direction enters FTD01 on `inside` and exits `outside`, then enters
FTD02 on `outside` and exits `inside`. The reverse is the mirror image.

## North-south per site

- EP11 → 1.1.1.1: FTD01 only (`ICMP inside 10.11.10.11 → outside 1.1.1.1`).
- EP21 → 1.1.1.1: FTD02 only.
- EP12 → 1.1.1.1: FTD01 only (`t1in 10.99.99.12 → outside 1.1.1.1`).
- EP22 → 1.1.1.1: FTD02 only.

## T1-IN symmetry

The `/32` host routes are EVPN Type-2:

```
10.99.99.12/32  via 10.1.1.2    internal, segid 50002, encap VXLAN
10.99.99.22/32  via 10.100.0.1  internal, segid 50002, encap VXLAN
```

C8K01 return routes (`VRF-OUTSIDE`):

```
10.99.99.0/24   -> 10.100.10.1
10.99.99.12/32  -> 10.100.10.1
10.99.99.22/32  -> 10.100.20.1
```

## NDFC sync

| Fabric | Switches | State |
|---|---|---|
| DC01 | BGW11, LF11, LF12, SPN11 | **In-Sync** |
| DC02 | BGW21, LF21, LF22, SPN21 | **In-Sync** |

Verified with `pendingConfig` (empty for all eight switches) and the fabric
overview (`Out-of-Sync: 0`).

## Reproduce

```bash
# host tests (console ports are tenant-1; adjust to your build)
python3 linux_console.py <EP11-port> "ping -c 5 10.22.10.21"
python3 linux_console.py <EP12-port> "ping -c 5 1.1.1.1"

# firewall state
python3 ftd_show.py 10.0.0.51 "show conn address 10.11.10.11"
python3 ftd_show.py 10.0.0.52 "show conn address 10.11.10.11"

# leaf EVPN host routes
python3 nxshow2.py 10.0.0.12 "show ip route vrf t1-in"

# NDFC sync
python3 nd_pcount.py
```
