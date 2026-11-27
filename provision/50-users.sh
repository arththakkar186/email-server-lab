#!/usr/bin/env bash
# 50-users.sh - lab mailbox accounts
#
# Mail users are Unix accounts with no login shell: they can authenticate to
# IMAP/SMTP through PAM but cannot SSH into the server. Passwords are random
# per build and written to a root-only file; nothing secret is stored in git.
set -euo pipefail

CREDS=/root/maillab-credentials.txt
OUT="${OUT:-/vagrant/out}"
umask 077
: > "$CREDS"

echo "==> [50] Mailbox users"
for u in ${LAB_USERS:-alice bob carol}; do
  if ! id "$u" &>/dev/null; then
    useradd --create-home --shell /usr/sbin/nologin --comment "MailLab user $u" "$u"
  fi
  pw="$(openssl rand -base64 18 | tr -d '/+=' | cut -c1-16)"
  echo "${u}:${pw}" | chpasswd
  echo "${u}@maillab.test  ${pw}" >> "$CREDS"
  # Create the Maildir now so the first IMAP login sees the special folders.
  sudo -u "$u" mkdir -p "/home/$u/Maildir"/{cur,new,tmp}
done

# Copy for the lab operator on the host (out/ is git-ignored).
install -m 0600 "$CREDS" "$OUT/maillab-credentials.txt"
echo "    Credentials written to $CREDS (and out/ on the host)"

# A welcome message proves local delivery (Postfix -> LMTP -> Maildir) works.
for u in ${LAB_USERS:-alice bob carol}; do
  printf 'Subject: Welcome to MailLab\n\nYour mailbox is ready.\n' | sendmail -f postmaster@maillab.test "${u}@maillab.test"
done
