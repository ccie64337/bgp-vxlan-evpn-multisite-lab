# IP / ASN / VNI Plan

## Management (`10.0.0.0/24`)

| Device | IP | Role |
|---|---|---|
| NDFC | 10.0.0.40 | Fabric controller |
| FMC | 10.0.0.50 | Firewall manager |
| FTD01 | 10.0.0.51 | DC1 firewall |
| FTD02 | 10.0.0.52 | DC2 firewall |
| C8K01 | 10.0.0.60 | WAN edge / DCI router |
| SPN11 | 10.0.0.10 | DC1 spine |
| LF11 | 10.0.0.11 | DC1 leaf |
| LF12 | 10.0.0.12 | DC1 leaf (FTD01) |
| BGW11 | 10.0.0.13 | DC1 border gateway |
| SPN21 | 10.0.0.20 | DC2 spine |
| LF21 | 10.0.0.21 | DC2 leaf (FTD02) |
| LF22 | 10.0.0.22 | DC2 leaf |
| BGW21 | 10.0.0.23 | DC2 border gateway |

## ASNs

| Device | AS |
|---|---|
| DC01 fabric (SPN11/LF11/LF12/BGW11) | 65001 |
| DC02 fabric (SPN21/LF21/LF22/BGW21) | 65002 |
| FTD01 | 65100 |
| FTD02 | 65101 |
| C8K01 | 65199 |

## VRFs / L3VNIs / RTs

| VRF | VNI | RT | Attached to |
|---|---|---|---|
| RED-IN | 50006 | `65001:50101` | LF11, LF12 |
| RED-OUT | 50007 | `65001:50102` | LF11, LF12, BGW11 |
| BLUE-IN | 50008 | `65002:50201` | LF21, LF22 |
| BLUE-OUT | 50009 | `65002:50202` | LF21, LF22, BGW21 |
| SHARED-OUT | 50010 | `65000:50300` | BGW11, BGW21 |
| T1-IN | 50002 | `65000:50099` | LF11, LF12, LF21, LF22, BGW11, BGW21 |

## Networks

| Network | Subnet | Gateway | VNI | VLAN | VRF |
|---|---|---|---|---|---|
| RED-NET | 10.11.10.0/24 | 10.11.10.1 | 30111 | 2330 | RED-IN |
| BLUE-NET | 10.22.10.0/24 | 10.22.10.1 | 30211 | 2340 | BLUE-IN |
| T1-NET | 10.99.99.0/24 | 10.99.99.1 | 30999 | 2399 | T1-IN |

Anycast gateway MAC: `2020.0000.00aa` on all host SVIs.

## Firewall p2p links

| Site | Link | FTD IP | Leaf IP | VRF |
|---|---|---|---|---|
| DC1 | inside | 10.255.10.1/29 | 10.255.10.4/29 (LF12 Vlan10) | RED-IN |
| DC1 | outside | 10.255.20.1/29 | 10.255.20.4/29 (LF12 E1/2) | RED-OUT |
| DC1 | T1-IN | 10.255.98.1/29 | 10.255.98.4/29 (LF12 Vlan99) | T1-IN |
| DC2 | inside | 10.255.11.1/29 | 10.255.11.4/29 (LF21 Vlan10) | BLUE-IN |
| DC2 | outside | 10.255.21.1/29 | 10.255.21.4/29 (LF21 E1/2) | BLUE-OUT |
| DC2 | T1-IN | 10.255.99.1/29 | 10.255.99.4/29 (LF21 Vlan99) | T1-IN |

FTD trunk: `G0/0` carries VLAN 10 (inside) and VLAN 99 (T1-IN); `G0/1` is the
routed outside port.

## BGW fusion / DCI

| Item | Value |
|---|---|
| BGW11 ↔ C8K01 | 10.100.10.1/30 ↔ 10.100.10.2 |
| BGW21 ↔ C8K01 | 10.100.20.1/30 ↔ 10.100.20.2 |
| BGW11 Lo30 | 10.255.30.1/32 (SHARED-OUT) |
| BGW21 Lo30 | 10.255.30.2/32 (SHARED-OUT) |
| DCI L3VNI | 50010, RT `65000:50300` |

## Hosts

| Node | Leaf / port | VLAN | VRF | IP | Gateway |
|---|---|---|---|---|---|
| EP11 | LF11 E1/1 | 2330 | RED-IN | 10.11.10.11/24 | 10.11.10.1 |
| EP12 | LF11 E1/2 | 2399 | T1-IN | 10.99.99.12/24 | 10.99.99.1 |
| EP21 | LF22 E1/1 | 2340 | BLUE-IN | 10.22.10.21/24 | 10.22.10.1 |
| EP22 | LF22 E1/2 | 2399 | T1-IN | 10.99.99.22/24 | 10.99.99.1 |

Host login: `root` / `lab` (change it for your own lab).

## EVE-NG notes

- Lab file: `topology/BGP_VXLAN_EVPN.unl`.
- The API session (tenant 0) and the GUI session (tenant 1) can create **two
  QEMU instances** per node. Keep the GUI (tenant-1) instances and kill the
  tenant-0 duplicates; otherwise the GUI telnet shows the baked IP
  (`10.99.99.10`) on every host.
- Console ports are dynamic; the tenant-1 ports in this build were:
  EP11 53983, EP12 35797, EP21 37011, EP22 56749.
