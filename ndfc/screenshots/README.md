# NDFC screenshots

Captured from Nexus Dashboard / NDFC 4.2.1.10 (`https://10.0.0.40`).

| File | View |
|---|---|
| `fabrics_list.png` | Manage → Fabrics: DC01, DC02, EDGE-WAN (MSD members) |
| `dc01_fabric.png` | DC01 fabric overview (AS 65001, fabric group MSD) |
| `dc01_inventory.png` | DC01 switches — all **In sync** |
| `dc01_segmentation.png` | DC01 Networks — RED-NET, T1-NET deployed; BLUE-NET NA |
| `dc01_vrfs.png` | DC01 VRFs — RED-IN/RED-OUT/SHARED-OUT/T1-IN deployed |
| `dc01_policies.png` | DC01 Configuration policies |
| `dc01_topology.png` | DC01 topology view |
| `dc02_fabric.png` | DC02 fabric overview (AS 65002) |
| `dc02_vrfs.png` | DC02 VRFs — BLUE-IN/BLUE-OUT/SHARED-OUT/T1-IN |

Status values in the UI: **Deployed** = attached and deployed,
**In sync** = running config matches the intended config, **Not applicable**
= the object belongs to the other site (e.g. BLUE-NET in DC01).
