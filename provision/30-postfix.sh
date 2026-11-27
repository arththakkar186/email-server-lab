#!/usr/bin/env bash
# 30-postfix.sh - Postfix MTA (SMTP 25 inbound, submission 587 for clients)
set -euo pipefail
SRC="${SRC:-/vagrant/config}"

echo "==> [30] Postfix"
export DEBIAN_FRONTEND=noninteractive
apt-get -y -qq install postfix

install -m 0644 "$SRC/postfix/main.cf"   /etc/postfix/main.cf
install -m 0644 "$SRC/postfix/master.cf" /etc/postfix/master.cf

# Aliases: role addresses go to real people.
cat > /etc/aliases <<'EOF'
postmaster: root
hostmaster: root
abuse:      root
root:       alice
it-team:    alice, bob
EOF
newaliases

# Users may only send as their own address on 587 (reject_sender_login_mismatch).
: > /etc/postfix/sender_login_maps
for u in ${LAB_USERS:-alice bob carol}; do
  echo "${u}@maillab.test ${u}" >> /etc/postfix/sender_login_maps
done
echo "it-team@maillab.test alice,bob" >> /etc/postfix/sender_login_maps
postmap /etc/postfix/sender_login_maps

postfix check
systemctl enable postfix
systemctl restart postfix
