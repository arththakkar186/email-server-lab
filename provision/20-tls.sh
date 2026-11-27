#!/usr/bin/env bash
# 20-tls.sh - private lab CA and a server certificate for mail.maillab.test
#
# A public CA cannot issue for a .test name, so the lab runs its own CA. The CA
# certificate (not the key) is copied to /vagrant/out/ so it can be imported
# into Thunderbird as a trusted authority.
set -euo pipefail

DIR=/etc/ssl/maillab
OUT="${OUT:-/vagrant/out}"
DAYS_CA=1825
DAYS_SRV=397

echo "==> [20] Lab certificate authority and server certificate"
install -d -m 0755 "$DIR"
install -d -m 0755 "$OUT"
cd "$DIR"

if [[ ! -f maillab-ca.key ]]; then
  openssl genrsa -out maillab-ca.key 4096
  chmod 0600 maillab-ca.key
  openssl req -x509 -new -key maillab-ca.key -sha256 -days "$DAYS_CA" \
    -subj "/C=CA/ST=Ontario/O=MailLab/CN=MailLab Root CA" \
    -out maillab-ca.crt
fi

cat > server.cnf <<'EOF'
[req]
distinguished_name = dn
req_extensions     = v3
prompt             = no
[dn]
C  = CA
ST = Ontario
O  = MailLab
CN = mail.maillab.test
[v3]
basicConstraints = critical, CA:FALSE
keyUsage         = critical, digitalSignature, keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName   = @san
[san]
DNS.1 = mail.maillab.test
DNS.2 = imap.maillab.test
DNS.3 = smtp.maillab.test
IP.1  = 192.168.56.10
EOF

openssl genrsa -out mail.maillab.test.key 2048
chmod 0600 mail.maillab.test.key
openssl req -new -key mail.maillab.test.key -config server.cnf -out mail.maillab.test.csr
openssl x509 -req -in mail.maillab.test.csr -CA maillab-ca.crt -CAkey maillab-ca.key \
  -CAcreateserial -days "$DAYS_SRV" -sha256 -extfile server.cnf -extensions v3 \
  -out mail.maillab.test.crt

openssl verify -CAfile maillab-ca.crt mail.maillab.test.crt
cp maillab-ca.crt "$OUT/maillab-ca.crt"
echo "    CA certificate for clients: $OUT/maillab-ca.crt"
