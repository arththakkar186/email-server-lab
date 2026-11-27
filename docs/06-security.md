# 06 · Security

## Controls by layer

| Layer | Control | Setting |
|---|---|---|
| Network | Isolated host-only network | No inbound path from the physical LAN or the internet |
| Host firewall | UFW default deny | Only 22, 25, 587, 993, 995 open, plus 53 from 192.168.56.0/24 |
| Brute force | fail2ban | 5 failures in 10 min → 1 h ban (sshd, postfix, postfix-sasl, dovecot) |
| Transport | TLS 1.2+ only | `smtpd_tls_protocols = !SSLv2, !SSLv3, !TLSv1, !TLSv1.1`, `ssl_min_protocol = TLSv1.2` |
| Transport | No plain-text logins | `smtpd_tls_auth_only = yes`, `disable_plaintext_auth = yes`, ports 110/143 closed |
| Identity | One auth source | Dovecot SASL over PAM for both SMTP and IMAP |
| Identity | No shell for mail users | `/usr/sbin/nologin` |
| Identity | No spoofing between users | `reject_sender_login_mismatch` + `sender_login_maps` |
| Relay | Not an open relay | `mynetworks = 127.0.0.0/8` and `smtpd_relay_restrictions = permit_mynetworks, permit_sasl_authenticated, reject_unauth_destination` |
| Recipients | No backscatter | `reject_unlisted_recipient` rejects unknown users during the SMTP session instead of sending a bounce later |
| Enumeration | No address harvesting | `disable_vrfy_command = yes` |
| Abuse | Protocol hygiene | `smtpd_helo_required`, `reject_invalid_helo_hostname`, `reject_non_fqdn_sender`, `reject_unauth_pipelining` |
| Abuse | Rate limits | 30 connections and 60 messages per client per minute (anvil) |
| Secrets | Nothing in git | Random passwords per build, written to a root-only file; private keys mode 600 and git-ignored |
| Patching | Unattended upgrades | Daily security updates |

## The open-relay rule in detail

An open relay accepts mail from anyone to anyone, and spammers find one within hours. Postfix checks
`smtpd_relay_restrictions` for every recipient:

```
permit_mynetworks            → the server itself (127.0.0.0/8) may relay
permit_sasl_authenticated    → logged-in users may relay
reject_unauth_destination    → everyone else may only send TO domains we host
```

A common mistake is adding the lab subnet (192.168.56.0/24) to `mynetworks` "so Thunderbird can send". That makes
every machine on the subnet an unauthenticated relay. In this lab Thunderbird authenticates on 587 like a real
client, and a unit test fails the build if `mynetworks` contains anything other than loopback.

**Proof** (from `90-verify.sh` and [08](08-testing.md)):
```
<~  RCPT TO:<victim@example.org>
 ~> 554 5.7.1 <victim@example.org>: Relay access denied
```

## TLS details

- Lab root CA: RSA 4096, 5 years. Server certificate: RSA 2048, 397 days (the browser/CA maximum for leaf certificates), SHA-256, SAN for mail/imap/smtp and the IP address.
- `smtpd_tls_security_level = may` on port 25: servers may use TLS but are not forced to (RFC 3207; forcing it would
  stop delivery from servers without TLS). On 587 it is `encrypt`, so clients must use TLS.
- The CA private key stays on the server with mode 600. In a real deployment it would be kept offline.

## Threats and mitigations

| Threat | Mitigation |
|---|---|
| Password sniffing on the network | TLS everywhere; plain-text ports closed |
| Password guessing | fail2ban, `auth_failure_delay`, strong random passwords |
| Spam relay | Relay restrictions, loopback-only mynetworks |
| A user spoofing another user | Sender-login matching on submission |
| Directory harvest (VRFY, RCPT probing) | VRFY disabled, rate limits, fail2ban `postfix` jail |
| DNS amplification | Recursion only for the lab ACL |
| Server compromise through a mail user | nologin shell, Postfix's privilege-separated chroot processes |
| Interception by a fake server | Clients verify the server certificate against the lab CA |

## What a production server would add

Public CA certificates (Let's Encrypt), DKIM signing, DMARC reporting, spam and virus filtering (Rspamd + ClamAV),
MTA-STS and TLS-RPT, encrypted backups of `/home/*/Maildir`, monitoring of the queue size, and an outbound smarthost if the ISP blocks port 25.
