#!/usr/bin/env bash
# 60-hardening.sh - host firewall, brute-force protection, automatic security updates
set -euo pipefail
SRC="${SRC:-/vagrant/config}"

echo "==> [60] Hardening"
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp    comment 'SSH (Vagrant / admin)'
ufw allow 25/tcp    comment 'SMTP inbound (MX)'
ufw allow 587/tcp   comment 'Submission (STARTTLS + AUTH)'
ufw allow 993/tcp   comment 'IMAPS'
ufw allow 995/tcp   comment 'POP3S'
ufw allow from 192.168.56.0/24 to any port 53 comment 'DNS for lab clients'
ufw --force enable

install -m 0644 "$SRC/fail2ban/jail.local" /etc/fail2ban/jail.local
systemctl enable fail2ban
systemctl restart fail2ban

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
EOF

ufw status verbose
fail2ban-client status
