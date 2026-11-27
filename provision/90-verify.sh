#!/usr/bin/env bash
# 90-verify.sh - server-side smoke tests run at the end of provisioning
set -euo pipefail

pass() { printf '  [PASS] %s\n' "$1"; }
fail() { printf '  [FAIL] %s\n' "$1"; FAILED=1; }
FAILED=0

echo "==> [90] Verification"
for svc in named postfix dovecot fail2ban; do
  systemctl is-active --quiet "$svc" && pass "$svc running" || fail "$svc not running"
done

for port in 25 53 587 993 995; do
  ss -ltn "( sport = :$port )" | grep -q LISTEN && pass "listening on $port" || fail "nothing on $port"
done
for port in 110 143; do
  ss -ltn "( sport = :$port )" | grep -q LISTEN && fail "plain-text port $port is open" || pass "plain-text $port closed"
done

[[ "$(dig +short MX maillab.test @127.0.0.1)" == "10 mail.maillab.test." ]] && pass "MX record" || fail "MX record"
[[ "$(dig +short -x 192.168.56.10 @127.0.0.1)" == "mail.maillab.test." ]] && pass "PTR record" || fail "PTR record"

echo | openssl s_client -connect 127.0.0.1:993 -servername mail.maillab.test \
  -CAfile /etc/ssl/maillab/maillab-ca.crt 2>/dev/null | grep -q "Verify return code: 0" \
  && pass "IMAPS certificate chain valid" || fail "IMAPS certificate"

echo | openssl s_client -starttls smtp -connect 127.0.0.1:587 -servername mail.maillab.test \
  -CAfile /etc/ssl/maillab/maillab-ca.crt 2>/dev/null | grep -q "Verify return code: 0" \
  && pass "Submission STARTTLS certificate valid" || fail "Submission STARTTLS"

sleep 2
compgen -G "/home/alice/Maildir/new/*" > /dev/null && pass "welcome mail delivered to alice's Maildir" \
  || fail "no mail in alice's Maildir"

# Open-relay check from an unauthenticated session: relaying to an outside domain must fail.
out="$(swaks --server 192.168.56.10 --port 25 --from test@example.net --to victim@example.org \
  --quit-after RCPT 2>&1 || true)"
grep -q "Relay access denied" <<<"$out" && pass "not an open relay" || fail "relay check (see swaks output)"

exit "$FAILED"
