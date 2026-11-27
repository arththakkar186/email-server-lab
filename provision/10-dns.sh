#!/usr/bin/env bash
# 10-dns.sh - BIND9 authoritative for maillab.test + caching resolver for the lab
set -euo pipefail
SRC="${SRC:-/vagrant/config}"

echo "==> [10] BIND9"
apt-get -y -qq install bind9 bind9utils

install -d -o root -g bind -m 0755 /etc/bind/zones
install -o root -g bind -m 0644 "$SRC/bind/db.maillab.test"    /etc/bind/zones/
install -o root -g bind -m 0644 "$SRC/bind/db.192.168.56"      /etc/bind/zones/
install -o root -g bind -m 0644 "$SRC/bind/named.conf.local"   /etc/bind/named.conf.local
install -o root -g bind -m 0644 "$SRC/bind/named.conf.options" /etc/bind/named.conf.options

# Fail the build if any zone or config file has a syntax error.
named-checkconf
named-checkzone maillab.test /etc/bind/zones/db.maillab.test
named-checkzone 56.168.192.in-addr.arpa /etc/bind/zones/db.192.168.56

systemctl enable --now named
systemctl restart named

# Point the server at its own resolver so Postfix sees the lab MX/A/PTR records.
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/maillab.conf <<EOF
[Resolve]
DNS=127.0.0.1
Domains=maillab.test
EOF
systemctl restart systemd-resolved

echo "    MX  -> $(dig +short MX maillab.test @127.0.0.1)"
echo "    PTR -> $(dig +short -x 192.168.56.10 @127.0.0.1)"
