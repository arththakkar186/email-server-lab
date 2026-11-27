# 04 · Build Procedure

This is the structured procedure for building the server by hand. Each step lists **actions**, then a
**check** that must pass before moving on. The `provision/` scripts automate exactly these steps, in the same order.

| Step | Script | Snapshot after |
|---|---|---|
| 1. Base OS | `00-common.sh` | `base-os` |
| 2. DNS | `10-dns.sh` | `dns-ok` |
| 3. Certificates | `20-tls.sh` | |
| 4. Postfix | `30-postfix.sh` | `postfix-ok` |
| 5. Dovecot | `40-dovecot.sh` | `dovecot-ok` |
| 6. Users | `50-users.sh` | |
| 7. Hardening | `60-hardening.sh` | |
| 8. Verify | `90-verify.sh` | `final` |
| 9. Client | `client.sh` + [07](07-thunderbird-client.md) | |

---

## Step 1 · Base operating system

**Actions**
1. Create the VM as in [03](03-virtual-environment.md) and install Ubuntu Server 20.04 (OpenSSH server selected, no snaps).
2. Set the host-only static address (netplan).
3. Set the name and time:
   ```bash
   sudo hostnamectl set-hostname mail.maillab.test
   echo "192.168.56.10 mail.maillab.test mail" | sudo tee -a /etc/hosts
   sudo timedatectl set-timezone America/Toronto
   sudo apt update && sudo apt -y upgrade
   sudo apt -y install dnsutils swaks mailutils ufw fail2ban
   ```

**Check**
```bash
hostname -f          # mail.maillab.test
ping -c2 192.168.56.1 # host reachable over host-only
timedatectl          # System clock synchronized: yes
```
Correct time matters: TLS certificate validation and log correlation both depend on it.

---

## Step 2 · DNS (BIND9)

**Actions**
1. `sudo apt -y install bind9 bind9utils`
2. Copy `config/bind/named.conf.options` and `named.conf.local` to `/etc/bind/`, and the two zone files to `/etc/bind/zones/`.
3. Check the syntax, then restart:
   ```bash
   sudo named-checkconf
   sudo named-checkzone maillab.test /etc/bind/zones/db.maillab.test
   sudo named-checkzone 56.168.192.in-addr.arpa /etc/bind/zones/db.192.168.56
   sudo systemctl restart named
   ```
4. Point the server at itself for DNS (systemd-resolved drop-in, see `10-dns.sh`).

**Check**
```bash
dig +short MX maillab.test        # 10 mail.maillab.test.
dig +short A mail.maillab.test    # 192.168.56.10
dig +short -x 192.168.56.10       # mail.maillab.test.
```
All three must agree. Mail servers reject or penalise senders whose forward and reverse DNS do not match.

---

## Step 3 · TLS certificates

**Actions**: run `20-tls.sh`, or by hand:
```bash
sudo mkdir -p /etc/ssl/maillab && cd /etc/ssl/maillab
# Lab root CA (keep this key private)
sudo openssl genrsa -out maillab-ca.key 4096
sudo openssl req -x509 -new -key maillab-ca.key -sha256 -days 1825 \
     -subj "/C=CA/ST=Ontario/O=MailLab/CN=MailLab Root CA" -out maillab-ca.crt
# Server key + CSR + certificate with subjectAltName (see server.cnf in the script)
sudo openssl genrsa -out mail.maillab.test.key 2048
sudo openssl req -new -key mail.maillab.test.key -config server.cnf -out mail.maillab.test.csr
sudo openssl x509 -req -in mail.maillab.test.csr -CA maillab-ca.crt -CAkey maillab-ca.key \
     -CAcreateserial -days 397 -sha256 -extfile server.cnf -extensions v3 -out mail.maillab.test.crt
sudo chmod 600 *.key
```

**Check**
```bash
openssl verify -CAfile maillab-ca.crt mail.maillab.test.crt     # OK
openssl x509 -in mail.maillab.test.crt -noout -ext subjectAltName
```
Modern clients ignore the CN and only check the **subjectAltName**. A certificate without a SAN produces a warning even if the CN is correct.

---

## Step 4 · Postfix

**Actions**
1. `sudo apt -y install postfix`. Choose *Internet Site*, system mail name `maillab.test`.
2. Install `config/postfix/main.cf` and `master.cf`.
3. Create `/etc/aliases` (postmaster → root → alice) and run `sudo newaliases`.
4. Create `/etc/postfix/sender_login_maps` (`alice@maillab.test alice`, ...) and run `sudo postmap /etc/postfix/sender_login_maps`.
5. `sudo postfix check && sudo systemctl restart postfix`

**Check**
```bash
sudo postconf -n | head            # shows the lab settings
sudo ss -ltnp | grep master        # :25 and :587 listening
swaks --server 127.0.0.1 --quit-after EHLO   # 250-STARTTLS present on 25
```

---

## Step 5 · Dovecot

**Actions**
1. `sudo apt -y install dovecot-core dovecot-imapd dovecot-pop3d dovecot-lmtpd`
2. Install `config/dovecot/99-maillab.conf` into `/etc/dovecot/conf.d/`.
3. `sudo doveconf -n` (prints the effective config; it fails on syntax errors).
4. `sudo systemctl restart dovecot && sudo systemctl restart postfix`. Postfix is restarted so it connects to the new sockets.

**Check**
```bash
ls -l /var/spool/postfix/private/{auth,dovecot-lmtp}  # both sockets exist, owned by postfix
sudo ss -ltnp | grep dovecot                           # :993 and :995 only
```

---

## Step 6 · Users

**Actions**
```bash
for u in alice bob carol; do
  sudo useradd -m -s /usr/sbin/nologin "$u"
  sudo passwd "$u"                 # choose a password (the script generates random ones)
  sudo -u "$u" mkdir -p /home/$u/Maildir/{cur,new,tmp}
done
echo "Welcome" | mail -s "Welcome" bob@maillab.test
```
`nologin` means these accounts can read mail but cannot open a shell on the server.

**Check**
```bash
sudo ls /home/bob/Maildir/new/                     # one message file
sudo doveadm auth test bob                         # passdb: bob auth succeeded
sudo grep "status=sent" /var/log/mail.log | tail -1  # relay=mail.maillab.test[private/dovecot-lmtp]
```

---

## Step 7 · Hardening

**Actions**: run `60-hardening.sh`: UFW allows 22, 25, 587, 993, 995, plus 53 from the lab subnet. fail2ban jails for sshd, postfix,
postfix-sasl and dovecot. Unattended security upgrades.

**Check**
```bash
sudo ufw status numbered
sudo fail2ban-client status        # 4 jails
```

---

## Step 8 · Verify

`sudo bash /vagrant/provision/90-verify.sh`. Every line must say PASS. See [08-testing.md](08-testing.md) for the full test set.

---

## Step 9 · Client

Build client01 ([03](03-virtual-environment.md)), import the lab CA and add both accounts in Thunderbird ([07](07-thunderbird-client.md)).
Send alice → bob and bob → alice, then reply and forward, and check the Sent folders on both sides.
