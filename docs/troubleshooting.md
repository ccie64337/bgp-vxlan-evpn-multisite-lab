# Troubleshooting / Gotchas

## NDFC

### `config-deploy` says “completed” but nothing changes

`switch_freeform_config` policies can be stuck at `status: NA` and the deploy
becomes a no-op. Fix:

1. Check `pendingConfig` and `config-preview` — they show the real delta.
2. Delete the stale `int_trunk_host` / redundant freeform policies.
3. Re-deploy the switch (or the fabric).
4. If a policy has an explicit `status: "NA"` key, `PUT` it back **without**
   that key so it behaves like the other deployable freeform policies.

### Stale `int_trunk_host` blocks the leaf

Auto-generated `int_trunk_host` policies on E1/1–E1/2 (trunk, `allowed none`)
conflict with the access/routed config. Delete those specific policies, then
deploy. They are the “trunk then access” lines you see in `pendingConfig`.

### VRF-name case causes a permanent Out-of-Sync

The running config renders VRF names lowercase (`red-out`, `shared-out`),
while the policy may use uppercase (`RED-OUT`, `SHARED-OUT`). The compliance
diff is case-only. Normalise the policy `CONF` to lowercase and deploy.

### HMM freeform policy stays `NA`

A standalone HMM `switch_freeform_config` (feature hmm / redistribute hmm) may
stay `NA` and never deploy. It is also redundant here: the `/32`s come from
EVPN Type-2 host routes. Remove it unless you specifically need HMM.

## FMC / FTD

- A subinterface `ifname` must **not** duplicate the parent’s `nameif`.
- The BGP object rejects the deprecated `maximumPaths` field.
- Deploy body needs `deviceList`; poll `metadata.task.id` for completion.
- FTD-side BGP peers are static; the leaf side uses prefix-based dynamic
  neighbors (`neighbor 10.255.x.0/29 remote-as 6510x`).

## EVE-NG

### All hosts show the same IP (`10.99.99.10`)

The API (tenant 0) and the GUI (tenant 1) can create **two QEMU instances** per
node. The GUI telnet lands on the tenant-1 instance, which still has the baked
image IP.

Fix: keep the tenant-1 instances, kill the tenant-0 duplicates, then set the
IPs on the tenant-1 consoles. If a host tap and its leaf port tap are on
different bridges, move the host tap:

```bash
brctl delif <old-bridge> <host-tap>
brctl addif <leaf-bridge> <host-tap>
```

A clean **Lab → Reload** removes all duplicates, but it reboots the topology.

### Autozoom is tiny / topology clipped

Off-canvas stale nodes (old endpoints) are included in “auto zoom to fit”.
Remove the stale nodes or crop the screenshot.

### Console ports change

EVE-NG re-allocates console ports on restart. The API `url` can be stale; use
the GUI console or look up the tenant-1 wrapper (`qemu_wrapper -C <port> -T 1`).

## C8K01 in NDFC

NDFC discovers C8K01 in `EDGE-WAN` but marks it `managable: false`: the default
SNMPv3 credential is MD5, and IOS-XE 17.15 forbids MD5 SNMPv3 users. Either
create a SHA-based credential or manage the few static routes once via console.

## Anycast / host routes

- The gateway is the leaf anycast SVI (`10.11.10.1`, `10.22.10.1`,
  `10.99.99.1`), not the FTD.
- The same anycast IP/MAC (`2020.0000.00aa`) exists on every leaf with the SVI,
  so the host always uses its local leaf.
- T1-IN `/32`s come from EVPN Type-2 (`segid 50002`); HMM is optional.
- North-south symmetry for T1-IN needs the per-host `/32` steering on C8K01
  and the BGW leaks. Without it, the shared `/24` can pull both sites to DC1.

## Symmetry risk

ECMP `maximum-paths 64` can still cause asymmetric inter-site paths in some
failover scenarios. Test 08 in the phase 2 log covers this.
