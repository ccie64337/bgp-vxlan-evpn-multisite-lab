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

## NX-OS verification commands

### Underlay / EVPN / VXLAN

| Check | Command | Expected |
|---|---|---|
| NVE peers | `show nve peers` | peer VTEPs Up |
| NVE VNIs | `show nve vni` | L2/L3 VNIs Up; multicast group |
| EVPN BGP | `show bgp l2vpn evpn summary` | Established, prefixes |
| EVPN routes | `show bgp l2vpn evpn` | Type-2 (MAC/IP) + Type-5 (prefix) |
| Type-5 DCI | `show bgp l2vpn evpn route-type prefix` | remote-site prefixes |
| Multicast BUM | `show ip mroute vrf <vrf>` | `(*,G)` / `(S,G)` entries |

### VRF routing and BGP

| Check | Command | Expected |
|---|---|---|
| VRF route table | `show ip route vrf red-in` / `blue-in` / `t1-in` / `red-out` / `blue-out` / `shared-out` | local + EVPN routes |
| FTD eBGP (leaf) | `show bgp ipv4 unicast summary vrf red-in` (etc.) | `10.255.x.1` AS 65100/65101 Established |
| T1-IN host `/32` | `show bgp ipv4 unicast vrf t1-in \| include 10.99.99` | `/32` via EVPN (`segid 50002`) |
| BGW leaks | `show ip route vrf shared-out` | `10.11.10.0/24`, `10.22.10.0/24`, `10.99.99.0/24` + `/32`s |
| BGW DCI | `show bgp ipv4 unicast summary vrf shared-out` | C8K01 + remote BGW Established |
| C8K01 return | `show ip route vrf VRF-OUTSIDE` | `.12/32 → 10.100.10.1`, `.22/32 → 10.100.20.1` |

### Anycast gateway / hosts

| Check | Command | Expected |
|---|---|---|
| Anycast MAC | `show fabric forwarding anycast-gateway-mac` | `2020.0000.00aa` |
| SVI mode | `show running-config interface vlan2399` | `fabric forwarding mode anycast-gateway` |
| ARP | `show ip arp vrf t1-in` | EP12/EP22 IP → MAC on `Vlan2399` |
| MAC table | `show mac address-table vlan 2399` | host MAC on the leaf port |
| EVPN MAC/IP | `show l2route evpn mac ip` | host MAC/IP entries |

### FTD peering (both sides)

| Side | Command | Expected |
|---|---|---|
| Leaf | `show bgp ipv4 unicast summary vrf red-in` | `10.255.10.1` AS 65100 |
| Leaf | `show bgp ipv4 unicast summary vrf t1-in` | `10.255.98.1` AS 65100 |
| Leaf | `show bgp ipv4 unicast summary vrf red-out` | `10.255.20.1` AS 65100 |
| FTD | `show bgp summary` | `10.255.10.4` / `.98.4` / `.20.4` AS 65001 |

## NDFC sync

| Fabric | Switches | State |
|---|---|---|
| DC01 | BGW11, LF11, LF12, SPN11 | **In-Sync** |
| DC02 | BGW21, LF21, LF22, SPN21 | **In-Sync** |

Verified with `pendingConfig` (empty for all eight switches) and the fabric
overview (`Out-of-Sync: 0`).

## Reproduce

On the hosts:

```bash
ping -c 5 10.22.10.21      # EP11 -> EP21
ping -c 5 1.1.1.1          # EP12 -> Internet
```

On a leaf/BGW (NX-OS):

```bash
show nve peers
show nve vni
show bgp l2vpn evpn summary
show bgp l2vpn evpn route-type prefix
show ip route vrf t1-in
show ip route vrf shared-out
show ip arp vrf t1-in
show mac address-table vlan 2399
show bgp ipv4 unicast summary vrf red-in
show bgp ipv4 unicast summary vrf t1-in
show bgp ipv4 unicast summary vrf red-out
```

On the FTD:

```bash
show conn address 10.11.10.11
show conn address 10.99.99.12
show bgp summary
```

NDFC pending config:

```bash
curl -k -H "AuthCookie: $TOKEN" \
  https://10.0.0.40/appcenter/cisco/ndfc/api/v1/lan-fabric/rest/control/fabrics/DC01/pendingConfig/9C6HJAC4YZD
```
