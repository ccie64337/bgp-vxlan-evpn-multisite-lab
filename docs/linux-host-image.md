# Lightweight Linux Host Image for EVE-NG

Built: 2026-11-10
Base: Debian 12 (bookworm) genericcloud amd64
Purpose: replace the docker `eve-gui-server` endpoints with a real Linux host
(full TCP/IP stack + validation tools) for the VXLAN EVPN lab.

## Image (single base image)

| Item | Value |
|---|---|
| EVE-NG image name | `linux-host` |
| Path | `/opt/unetlab/addons/qemu/linux-host/virtioa.qcow2` |
| Format | qcow2, 4 GiB virtual, ~668 MB actual |
| Login | `root` / `lab` |
| Default IP | 10.99.99.10/24, gw 10.99.99.1 (set per node in the console) |
| Hostname | `linux-host` |
| Console | serial `ttyS0` + VGA `tty0`; lab nodes are set to **telnet** (template default is VNC) |
| NIC | virtio-net-pci; `systemd-networkd`; `net.ifnames=0` → `eth0` |
| MD5 | `389315430b4d4ee1326542f304dfb2f4` |

One image is enough for any number of host nodes. Add the node with this image,
then set the per‑node address in the console:

```
# example: EP22 -> 10.99.99.22/24
printf "[Match]\nName=e*\n\n[Network]\nAddress=10.99.99.22/24\nGateway=10.99.99.1\nDNS=1.1.1.1\n" \
  > /etc/systemd/network/10-eth0.network
systemctl restart systemd-networkd
```

Additional images can be added later through the EVE-NG GUI (System → File
manager / image import).

## Deployed hosts (4)

| Node | Leaf / port | Access VLAN | VRF | IP | Gateway |
|---|---|---|---|---|---|
| EP11 | LF11 E1/1 | 2330 | RED‑IN | 10.11.10.11/24 | 10.11.10.1 |
| EP12 | LF11 E1/2 | 2399 | T1‑IN | 10.99.99.12/24 | 10.99.99.1 |
| EP21 | LF22 E1/1 | 2340 | BLUE‑IN | 10.22.10.21/24 | 10.22.10.1 |
| EP22 | LF22 E1/2 | 2399 | T1‑IN | 10.99.99.22/24 | 10.99.99.1 |

T1‑IN is the stretched VRF (VLAN 2399 / VNI 30999) present on all four leafs,
so EP12 and EP22 share `10.99.99.0/24` across sites.

## EVE‑NG console / tenant caveat

The lab is opened by the admin API session in **tenant 0** and by the GUI user
in **tenant 1**. Starting a node from both creates **two QEMU instances per
node**, each with its own console port and its own tap set. Symptoms:

- The GUI telnet shows the baked `10.99.99.10` on every host (you are on the
  tenant‑1 instance).
- The API `url` port points at the tenant‑0 instance (which may be stopped).
- Taps land on different bridges (`vnet001…` vs `vnet002…`), so the host MAC
  never reaches the leaf.

Workaround used: keep the **tenant‑1** instances (the GUI ones), kill the
tenant‑0 duplicates, then set the IPs on the tenant‑1 consoles. If a host tap
and its leaf port tap are on different bridges, move the host tap to the leaf
bridge:

```
brctl delif <old-bridge> <host-tap>
brctl addif <leaf-bridge> <host-tap>
```

A clean lab reload (Lab → Reload) removes all duplicates and recreates one
instance/tap per node; it has not been run yet.

## Installed tools

`iproute2 iputils-ping traceroute mtr-tiny dnsutils curl wget
netcat-openbsd socat tcpdump arping ethtool iperf3 openssh-server python3
chrony jq conntrack nmap less vim-tiny ca-certificates bash-completion`

## Add to EVE-NG (UI)

1. Add a node → template **Linux**, image **linux-host**.
2. 1 × virtio NIC.
3. Connect the four hosts:
   - EP11 → **LF11 E1/1** (access VLAN 2330, RED‑IN)
   - EP12 → **LF11 E1/2** (access VLAN 2399, T1‑IN)
   - EP21 → **LF22 E1/1** (access VLAN 2340, BLUE‑IN)
   - EP22 → **LF22 E1/2** (access VLAN 2399, T1‑IN)
4. 1 vCPU / 1024 MB, console **telnet**, start and log in `root` / `lab`.
5. Set the per‑node IP (see the deployed‑hosts table above) with the
   `systemd-networkd` snippet.

## Rebuild recipe

```bash
curl -L -o base.qcow2 \
  https://cloud.debian.org/images/cloud/bookworm/latest/debian-12-genericcloud-amd64.qcow2
qemu-img resize base.qcow2 4G
LIBGUESTFS_BACKEND=direct virt-customize -a base.qcow2 \
  --hostname linux-host \
  --root-password password:lab \
  --install "iproute2,iputils-ping,traceroute,mtr-tiny,dnsutils,curl,wget,netcat-openbsd,socat,tcpdump,arping,ethtool,iperf3,openssh-server,python3,chrony,jq,conntrack,nmap,less,vim-tiny,ca-certificates,bash-completion" \
  --run-command 'printf "network: {config: disabled}\n" > /etc/cloud/cloud.cfg.d/99-disable-network-config.cfg' \
  --run-command 'printf "[Match]\nName=e*\n\n[Network]\nAddress=10.99.99.10/24\nGateway=10.99.99.1\nDNS=1.1.1.1\n" > /etc/systemd/network/10-eth0.network' \
  --run-command "sed -i 's/consoleblank=0/consoleblank=0 net.ifnames=0/' /etc/default/grub" \
  --run-command 'update-grub' \
  --run-command 'systemctl enable serial-getty@ttyS0.service systemd-networkd.service ssh.service' \
  --run-command "sed -i 's/^#*PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config" \
  --run-command 'apt-get clean' \
  --truncate /etc/machine-id
```

Upload:
```bash
scp base.qcow2 root@<eve-ng>:/opt/unetlab/addons/qemu/linux-host/virtioa.qcow2
ssh root@<eve-ng> /opt/unetlab/wrappers/unl_wrapper -a fixpermissions
```
