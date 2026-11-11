# Cisco Data Center Segmentation — Reference Collection

**Topic:** VRF-based (macro) segmentation vs micro-segmentation (VXLAN GPO / SGT / PVLAN), and how to place an application with its dependencies (DB, etc.) in a VXLAN EVPN fabric.

**Collected:** 2026-11-06
**Applies to:** the `asa_ndfc_lab` environment — Nexus Dashboard `10.0.0.40`, build `4.2.1.10` (NDFC `12.5.0.475`), fabric `MSD` with members `DC01`/`DC02`, switches N9K-C9300v on NX-OS `10.6(3)`.

**Purpose:** keep the Cisco sources used for the segmentation design discussion traceable, with an honest record of which documents were read in full and which are further reading.

---

## 0. Evidence status legend

| Status | Meaning |
|---|---|
| **READ** | Opened and read; the quoted statements were taken from it |
| **SURFACED** | Appeared in search results with title/snippet only; **not** read in full. Treat as further reading, not as a source of specific quotes |
| **VERIFIED-LIVE** | Confirmed directly against this lab's devices/APIs (not a Cisco document) |

> Important: only the primary whitepaper and the NDFC multi-site guides were read in full. Everything else is listed for completeness.

---

## 1. Primary source — READ

### 1.1 Securing Data Centers with Microsegmentation using VXLAN GPO

- **Type:** Cisco White Paper
- **Updated:** August 20, 2025
- **Status:** **READ**
- **URL:** <https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.html>
- **PDF:** <https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/securing-datacenters-with-microsegmentation-and-vxlan-gpo.pdf>

This is the source of essentially every substantive claim in the segmentation discussion.

#### Sections used, and what each supports

| Section | What it establishes |
|---|---|
| Introduction / VXLAN GPO | Segmentation traditionally done with PVLAN + ACLs; PVLAN segments only within a broadcast domain; PVLAN/ACL do not scale to modern east-west traffic; GPO was introduced for that gap |
| Use-Cases → **VRF as a Security Zone** | A VRF groups resources into one zone with strict isolation from other VRFs — but communication **inside** the VRF is unrestricted |
| Use-Cases → **Subnet as a Security Zone** | Alternative is firewall-as-default-gateway for inter-subnet control, at the cost of an east-west bottleneck |
| Use-Cases → **Application as a Security Zone** | Group application components (e.g. App vs DB) into Security Groups and write contracts between them |
| **VRF Enforcement Mode** | Unenforced / Default-Permit (black-list) / Default-Deny (white-list); brownfield migration guidance |
| **Support on Nexus 9000 Switches** | Feature availability by NX-OS release (Table 1) and by platform (Table 2) |
| **Security Group Routing Template** | Requires a dedicated Policy TCAM carve-out and a **device reload** |
| **Security Group / SGT / Contract** | SG = logical container; SGT = 16-bit tag in the VXLAN-GBP header; contracts = SGACLs |
| **Network-centric vs Host-centric approach** | Network-centric = "macro-segmentation"; host-centric = "micro-segmentation" |

#### Key quotations

On VRF as a security zone (the basis for "a VRF does not isolate app from DB"):

> "This method alone is sufficient to ensure that traffic remains isolated between VRFs, allowing **unrestricted communication only within each individual VRF**."

On PVLAN vs GPO:

> "While a PVLAN based solution was used to provide segmentation within the same broadcast domain by using constructs like Primary and Secondary (Isolated and Community) VLANs, segmentation within a broadcast domain is often referred to as Micro Segmentation."

> "Unlike legacy solutions such as PVLAN, which provides enforcement only within a broadcast domain, VXLAN GPO allows to perform enforcement at the VRF (and even inter-VRF) level."

> "GPO … makes it much more scalable compared to a PVLAN/ACL based segmentation approach."

On firewall-as-gateway as the alternative:

> "…by directing all inter-subnet communications through a centralized firewall, the model introduces a potential performance bottleneck … the volume of East-West traffic … can quickly exceed the capacity of these devices."

#### Platform-support evidence (critical for this lab)

The whitepaper's **Table 2 — VXLAN GPO support on Nexus 9000 series switches** lists:

| Platform | ESG Selectors | SGACLs |
|---|---|---|
| N9300-FX / FX3 / GX / GX2B / HX | 8000 | 64000 |
| N9300-FX2 / GX2A, Nexus 9408 | 8000 | 32000 |

**N9K-C9300v (the N9Kv used in this lab) is not listed.** Table 1 also shows GPO first appeared in **NX-OS 10.4(3)F** with platform/selector additions in later releases. This is the documentary basis for "GPO is not supported on this platform".

#### Feature prerequisites captured

- Dedicated **Policy TCAM** for SGACLs (separate from the ACL/Classification TCAM).
- **Security Group Routing Template** must be enabled, and the device **must be reloaded**.
- ARP suppression is required in conjunction with GPO deployments.
- Scale: 8000 ESG selectors / 32 000–64 000 SGACLs per device (supported hardware).

---

## 2. Cisco Live sessions — SURFACED

Not read in full; listed as further reading. Titles and links taken from search results.

| Session | Title | Link |
|---|---|---|
| **BRKDCN-2629** (2024) | Design and Automate Micro-Segmentation in NX-OS VXLAN EVPN Fabrics Using VXLAN Group Policy Option (GPO) and NDFC | <https://www.ciscolive.com/c/dam/r/ciscolive/global-event/docs/2024/pdf/BRKDCN-2629.pdf> |
| **BRKDCN-2933** (EMEA 2025) | Deployment of Micro-Segmentation in Cisco NX-OS VXLAN EVPN Fabrics | <https://www.ciscolive.com/c/dam/r/ciscolive/emea/docs/2025/pdf/BRKDCN-2933.pdf> |
| **BRKDCN-2930** (2025) | Secure Networking & Segmentation for Multicloud Architectures | <https://www.ciscolive.com/c/dam/r/ciscolive/global-event/docs/2025/pdf/BRKDCN-2930.pdf> |
| **BRKDCN-2930** (2026) | Designing Zero Trust Data Center Segmentation Architecture | <https://www.ciscolive.com/c/dam/r/ciscolive/global-event/docs/2026/pdf/BRKDCN-2930.pdf> |
| **BRKDCN-2959** (2025) | Turbo charge your ACI Segmentation and Visibility (ACI uSeg / contracts) | <https://www.ciscolive.com/c/dam/r/ciscolive/global-event/docs/2025/pdf/BRKDCN-2959.pdf> |
| **BRKDCN-2929** (2023) | Simple VXLAN/EVPN Fabric Setup with Nexus Dashboard — contains the "Tenants (VRF)" framing | <https://www.ciscolive.com/c/dam/r/ciscolive/emea/docs/2023/pdf/BRKDCN-2929.pdf> |

Also surfaced: a SlideShare copy of BRKDCN-2629 and an ACI-segmentation deck (BRKDCN-2959), both secondary/third-party hosting.

---

## 3. Cisco product documentation

| Document | Relevance | Status | Link |
|---|---|---|---|
| Nexus 9000 Series NX-OS VXLAN Configuration Guide, Release **10.6(x)** — *Microsegmentation for VXLAN Fabrics Using GPO* | CLI-level GPO reference for this lab's NX-OS train | SURFACED | <https://www.cisco.com/c/en/us/td/docs/dcn/nx-os/nexus9000/106x/configuration/vxlan/cisco-nexus-9000-series-nx-os-vxlan-configuration-guide-release-106x/microsegmentation_for_vxlan_fabrics_using_gpo.html> |
| Nexus 9000 VXLAN BGP EVPN Data Center Fabrics — Design and Implementation Guide | VRF / VNI / tenant design model; macro-segmentation baseline | SURFACED | <https://www.cisco.com/c/en/us/td/docs/dcn/whitepapers/cisco-vxlan-bgp-evpn-design-and-implementation-guide.html> |
| VXLAN EVPN Multi-Site Design and Deployment White Paper | MSD / DCI context used by this lab | SURFACED | <https://www.cisco.com/c/en/us/products/collateral/switches/nexus-9000-series-switches/white-paper-c11-739942.html> |

### 3.1 NDFC multi-site documentation — READ

| Document | Relevance | Status | Link |
|---|---|---|---|
| NDFC Configuration Guide 12.x — *Multi-Site Domain for VXLAN BGP EVPN Fabrics* | The MSD creation / member-fabric / deploy procedure executed in this lab | **READ** | <https://www.cisco.com/c/en/us/td/docs/dcn/ndfc/121x/configuration/fabric-controller/cisco-ndfc-fabric-controller-configuration-guide-121x/msd-for-vxlan-bgp-evpn-fabrics.html> |
| NDFC 12.2.2 / 12.2.3 — *VXLAN EVPN Multi-Site* tech article | MSD field reference and the recalculate/deploy-level matrix | **READ** | <https://www.cisco.com/c/en/us/td/docs/dcn/ndfc/1222/articles/ndfc-vxlan-evpn-multi-site/vxlan-evpn-multi-site.html> |

---

## 4. Cisco security / segmentation frameworks — SURFACED

| Document | Key statement | Link |
|---|---|---|
| **A Framework to Protect Data Through Segmentation** (Cisco Security) | Segmentation as part of a defence-in-depth / zero-trust model; VLAN+ACL alone gives only limited separation | <https://sec.cloudapps.cisco.com/security/center/resources/framework_segmentation.html> |
| **Segmentation Strategy** (Cisco Community, Security KB) | "You can choose either VN (Macro) or SGT (Micro) or both segmentation options" | <https://community.cisco.com/t5/security-knowledge-base/segmentation-strategy/ta-p/3757424> |
| **SD-Access Segmentation Design Guide** (Cisco Community) | "VRFs provide complete isolation of routing and switching environments" | <https://community.cisco.com/t5/networking-knowledge-base/sd-access-segmentation-design-guide/ta-p/4935734> |

---

## 5. Webinars / video — SURFACED

| Item | Link |
|---|---|
| DC Segmentation with VXLAN Group Policy Object (GPO) — Cisco on-demand webinar | <https://video.cisco.com/detail/video/6369679986112> |
| Micro-segmentation on VXLAN-EVPN fabric with Nexus Dashboard — Cisco webinar | <https://www.cisco.com/c/en/us/customer-success/video/webinar/micro-segmentation-on-vxlan-evpn-fabric-with-nexus-dashboard.html> |
| YouTube — *Micro-segmentation in Cisco NX-OS VXLAN EVPN fabrics using VXLAN GPO* (playlist) | <https://www.youtube.com/playlist?list=PLzBHOBCurcXT2fpHxd-j4y_ZlTBMA4OzP> |

---

## 6. Claim → reference matrix

| Claim | Reference |
|---|---|
| Segmentation traditionally = PVLAN (intra-broadcast-domain) + ACL (inter-domain) | GPO White Paper — *Introduction / VXLAN GPO* |
| PVLAN is legacy, L2-only, broadcast-domain-scoped, does not scale | GPO White Paper — *Introduction*, *VRF Enforcement Mode* |
| Traffic **inside** a VRF is unrestricted → a VRF does not isolate app from DB | GPO White Paper — *VRF as a Security Zone* |
| GPO enforces at VRF and inter-VRF level | GPO White Paper — *VRF Enforcement Mode* |
| GPO scales better than PVLAN/ACL because SGACLs use a dedicated Policy TCAM | GPO White Paper — *Security Group Routing Template* |
| Recommended model = VRF (macro) + GPO/SGT (micro), layered | GPO White Paper — *VRF / Subnet / Application as a Security Zone*; Cisco Community *Segmentation Strategy* |
| Firewall-as-default-gateway is the non-GPO alternative, with an east-west bottleneck | GPO White Paper — *Subnet as a Security Zone* |
| GPO needs the Security Group Routing Template + a reload | GPO White Paper — *Security Group Routing Template* |
| GPO first appeared in NX-OS 10.4(3)F | GPO White Paper — Table 1 |
| GPO supported platforms exclude N9K-C9300v | GPO White Paper — Table 2 |
| VRF is the fabric-level "tenant" construct (NDFC) | BRKDCN-2929 ("Tenants (VRF)"); this repo's `docs/` and live API evidence |
| MSD process: create MSD → move members → recalc/deploy → create VRF/network at MSD | NDFC *Multi-Site Domain for VXLAN BGP EVPN Fabrics* (READ) |

---

## 7. Applicability to this lab — VERIFIED-LIVE

Facts confirmed directly against the running environment (not from Cisco documentation):

| Finding | How verified |
|---|---|
| Fabric is `MSD` (MFD) with members `DC01` (site 1) and `DC02` (site 2) | `GET /control/fabrics/msd/fabric-associations` |
| Switches are **N9K-C9300v**, NX-OS **10.6(3)** | `show inventory`, `show version` |
| NDFC rejects `layer2` + VRF without micro-segmentation: *"Security groups and MAC segmentation need to be enabled to create networks for layer-2 with VRF"* | `POST /api/v1/manage/fabrics/MSD/networks` → HTTP 207 with `status: failed` |
| Tenant VRF `APP-A-VRF` (L3 VNI 50001) + network `WEB-NET` (VLAN 2300, L2 VNI 30000, `layer3`, anycast GW `192.168.10.1/24`) deployed to LF11/LF12 (DC01) and LF21/LF22 (DC02) | `show vrf`, `show ip interface brief vrf`, `show nve vni` |
| Multi-site overlay eBGP EVPN between BGW11 (`10.1.0.2`) and BGW21 (`10.2.0.1`) is Up | `show bgp l2vpn evpn summary` |
| Multisite VTEP VIP loopbacks `10.100.0.1` / `10.100.0.2` required a manual `no shutdown` after MSD deploy | `show interface loopback100` |

**Conclusion drawn:** on this platform, VRF-based segmentation is the only supported segmentation tier; GPO/SGT micro-segmentation is not available, and PVLAN is not a viable substitute.

---

## 8. How to verify the "GPO not supported on N9Kv" claim yourself

1. Open the GPO whitepaper → section **Support on Nexus 9000 Switches**.
2. Compare **Table 2** platforms against your `show inventory` output (`PID: N9K-C9300v`). The virtual chassis is not listed.
3. Check the NX-OS VXLAN Configuration Guide for 10.6(x) → *Microsegmentation for VXLAN Fabrics Using GPO* for any virtual-platform caveat.
4. Cross-check in NDFC: attempt to enable Security Groups / MAC segmentation on the fabric — the platform will refuse if unsupported.

> Caveat: absence from the table is strong evidence but not a formal statement that the feature cannot run on the virtual platform. If this matters for a production decision, confirm with Cisco TAC or an authorized N9Kv feature-support matrix.

---

## 9. Open items / not yet read

| Item | Note |
|---|---|
| BRKDCN-2629 / BRKDCN-2933 slide content | Only titles/snippets available; the VRF-vs-GPO design-choice slides have not been extracted |
| BRKDCN-2930 (2026) | Not opened — likely the best source for the "layered zero-trust segmentation" argument |
| NX-OS 10.6 GPO guide | Not opened — needed to confirm virtual-platform caveats and exact CLI |
| Cisco TrustSec / ISE integration for SGT | Not researched; relevant only if GPO becomes available |

---

## 10. Related documents in this repository

| File | Contents |
|---|---|
| `reports/nexus-asa-peering-discovery.md` | Read-only discovery of the earlier NDFC↔ASA peering |
| `reports/narm-peering-configuration.md` | NARM service-insertion / peering configuration (archived state) |
| `reports/narm-peering-api-response.json` | Raw API evidence for the above |
| `docs/firewall-as-gateway-workflow.md` | Firewall-as-Gateway implementation workflow |
| `docs/firewall-as-gateway-architecture.md` | Architecture and object model |
| `docs/firewall-as-gateway-validation.md` | Validation layers |
| `docs/firewall-as-gateway-troubleshooting.md` | Failure history |

---

*End of reference collection.*
