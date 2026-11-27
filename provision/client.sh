#!/usr/bin/env bash
# client.sh - client01: Ubuntu desktop guest with Thunderbird
set -euo pipefail
SRC="${SRC:-/vagrant/config}"
OUT="${OUT:-/vagrant/out}"

echo "==> [client] Desktop, Thunderbird, lab DNS and CA trust"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get -y -qq install --no-install-recommends xubuntu-core thunderbird dnsutils swaks

# Use the lab DNS server so mail.maillab.test resolves.
mkdir -p /etc/systemd/resolved.conf.d
cat > /etc/systemd/resolved.conf.d/maillab.conf <<EOF
[Resolve]
DNS=192.168.56.10
Domains=maillab.test
EOF
systemctl restart systemd-resolved

# Trust the lab CA at OS level (Thunderbird has its own store: see docs/07).
if [[ -f "$OUT/maillab-ca.crt" ]]; then
  install -m 0644 "$OUT/maillab-ca.crt" /usr/local/share/ca-certificates/maillab-ca.crt
  update-ca-certificates
fi

# Auto-configuration file: Thunderbird reads <install dir>/isp/<domain>.xml.
install -d /usr/lib/thunderbird/isp
install -m 0644 "$SRC/thunderbird/maillab.test.xml" /usr/lib/thunderbird/isp/maillab.test.xml

dig +short MX maillab.test
