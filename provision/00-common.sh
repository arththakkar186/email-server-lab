#!/usr/bin/env bash
# 00-common.sh - base OS settings for mail01 (Ubuntu Server 20.04 LTS guest)
set -euo pipefail

LAB_IP="${LAB_IP:-192.168.56.10}"
FQDN="mail.maillab.test"

echo "==> [00] hostname, hosts file, time, packages"
hostnamectl set-hostname "$FQDN"
if ! grep -q "$FQDN" /etc/hosts; then
  echo "$LAB_IP $FQDN mail ns1.maillab.test ns1" >> /etc/hosts
fi

timedatectl set-timezone America/Toronto
timedatectl set-ntp true

export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get -y -qq upgrade
apt-get -y -qq install ca-certificates curl dnsutils net-tools swaks mailutils \
  openssl ufw fail2ban unattended-upgrades

# Answer Postfix's installer questions up front so the install is non-interactive.
debconf-set-selections <<EOF
postfix postfix/main_mailer_type select Internet Site
postfix postfix/mailname string maillab.test
EOF
echo "maillab.test" > /etc/mailname
