#!/usr/bin/env bash
# 40-dovecot.sh - Dovecot IMAPS/POP3S, LMTP delivery and SASL for Postfix
set -euo pipefail
SRC="${SRC:-/vagrant/config}"

echo "==> [40] Dovecot"
export DEBIAN_FRONTEND=noninteractive
apt-get -y -qq install dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd

install -m 0644 "$SRC/dovecot/99-maillab.conf" /etc/dovecot/conf.d/99-maillab.conf

# Print the effective config; a syntax error stops the build here.
doveconf -n > /dev/null

systemctl enable dovecot
systemctl restart dovecot
# Postfix must be restarted after Dovecot creates the auth and LMTP sockets.
systemctl restart postfix

ls -l /var/spool/postfix/private/auth /var/spool/postfix/private/dovecot-lmtp
