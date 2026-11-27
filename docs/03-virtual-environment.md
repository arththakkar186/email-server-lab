# 03 · Virtual Environment

## Host

| Item | Value |
|---|---|
| Host OS | Windows 10, macOS or Linux |
| Hypervisor | Oracle VirtualBox 6.1 with the Extension Pack |
| Host resources used | 2 + 2 vCPU, 2 GB + 3 GB RAM, about 40 GB disk |
| Automation (2026) | Vagrant 2.2+ with the `ubuntu/focal64` box |

## Networks

Each guest has two virtual network adapters:

| Adapter | VirtualBox mode | Subnet | Purpose |
|---|---|---|---|
| 1 | **NAT** | 10.0.2.0/24 (per VM, isolated) | Outbound internet for `apt` only. Nothing outside can connect in |
| 2 | **Host-only** (`vboxnet0`) | 192.168.56.0/24 | All lab traffic: client ↔ server, and host ↔ server for SSH and testing |

```
                ┌───────────────────── Physical host ──────────────────────┐
                │                                                           │
 Internet ◄─NAT─┤ mail01  enp0s3 10.0.2.15   enp0s8 192.168.56.10 ──┐       │
                │                                                   │       │
 Internet ◄─NAT─┤ client01 enp0s3 10.0.2.15  enp0s8 192.168.56.20 ──┼─ vboxnet0 (host 192.168.56.1)
                │                                                   │       │
                └───────────────────────────────────────────────────┘
```

Why not one **bridged** adapter? Bridged mode puts the VMs on the physical LAN (a campus or home network). That would
expose an SMTP server to other users, and its address changes from network to network. Host-only plus NAT
keeps the lab isolated and the addresses stable.

Why not **NAT Network**? It works too, but host-only lets the physical host reach the server directly (for
SSH and running the test script) without port forwarding.

## Virtual machines

| Setting | mail01 | client01 |
|---|---|---|
| Guest OS | Ubuntu Server 20.04 LTS (64-bit) | Xubuntu 20.04 desktop, or Windows 10 |
| vCPU / RAM | 2 / 2048 MB | 2 / 3072 MB |
| Disk | 20 GB VDI, dynamically allocated | 25 GB VDI |
| Adapter 1 | NAT | NAT |
| Adapter 2 | Host-only vboxnet0, 192.168.56.10 static | Host-only vboxnet0, 192.168.56.20 static |
| DNS | 127.0.0.1 (its own BIND) | 192.168.56.10 |
| Display | Headless | 64 MB VRAM, bidirectional clipboard |
| Guest additions | Not needed | Installed for clipboard and screen resizing |

## Static addressing (manual build)

On mail01, `/etc/netplan/60-hostonly.yaml`:

```yaml
network:
  version: 2
  ethernets:
    enp0s8:
      addresses: [192.168.56.10/24]
      nameservers:
        addresses: [127.0.0.1]
        search: [maillab.test]
```

`sudo netplan apply`, then check with `ip -4 addr show enp0s8`.

On a Windows 10 client: Control Panel → Network Connections → *Ethernet 2* (host-only) → IPv4 → address
192.168.56.20/24, no gateway (the NAT adapter provides the default route), DNS 192.168.56.10.

## Snapshots

Take a snapshot after each major step in [04-build-procedure.md](04-build-procedure.md) (`base-os`, `dns-ok`,
`postfix-ok`, `dovecot-ok`, `final`). If a later step breaks something, restoring a snapshot gets you back in seconds
instead of rebuilding. With Vagrant: `vagrant snapshot save mail01 dovecot-ok`.
