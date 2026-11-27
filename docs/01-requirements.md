# 01 · Requirements and Scope

## Objective

Build a working email system in a virtual environment: a mail server on a guest operating system and a
desktop email client (Mozilla Thunderbird) on another guest. Users must be able to send and receive mail between
accounts, the build must follow a documented procedure, and each step must be verified.

## Learning outcomes covered

1. Install and configure a server OS as a virtual machine guest.
2. Understand how SMTP, IMAP and POP3 work together, and the roles of an MTA, MDA and MUA.
3. Set up DNS records that make a mail domain work (MX, A, PTR).
4. Secure mail with TLS and authenticated submission.
5. Configure a mail client and fix connection problems using server logs.

## Roles in an email system

| Role | Full name | In this lab | Job |
|---|---|---|---|
| MUA | Mail User Agent | Thunderbird | Write, send and read mail |
| MSA | Mail Submission Agent | Postfix `submission` on 587 | Accept mail from authenticated users |
| MTA | Mail Transfer Agent | Postfix `smtpd`/`smtp` on 25 | Route mail between servers |
| MDA | Mail Delivery Agent | Dovecot LMTP | Put mail in the right mailbox |
| MRA / IMAP server | Mail Retrieval Agent | Dovecot IMAP/POP3 | Let users read stored mail |

## Requirements

| ID | Requirement | Met by |
|---|---|---|
| R1 | Server runs as a guest OS in a virtual environment | Ubuntu Server 20.04 guest in VirtualBox |
| R2 | Client runs Thunderbird on a separate guest | client01 (Xubuntu or Windows 10) |
| R3 | At least three user mailboxes | alice, bob, carol |
| R4 | Send between users | Postfix submission → LMTP → Maildir |
| R5 | Read with IMAP, and POP3 as an option | Dovecot 993 / 995 |
| R6 | Mail domain resolvable by name | BIND9 zone `maillab.test` with MX |
| R7 | Passwords never sent in clear text | TLS required on 587/993/995; plain-text ports closed |
| R8 | Server must not be an open relay | `reject_unauth_destination`, mynetworks = loopback only |
| R9 | Documented, repeatable procedure | [04-build-procedure.md](04-build-procedure.md) and `provision/` |
| R10 | Evidence that it works | [08-testing.md](08-testing.md), `90-verify.sh`, `mail_e2e_test.py` |

## Constraints

- Isolated lab: no public IP and no real domain, so mail stays inside `maillab.test`. Sending to the internet
  is out of scope (most ISPs block outbound port 25, and a .test domain cannot be delivered to).
- Host resources: about 8 GB RAM and 4 cores available, so the server gets 2 GB and the client 3 GB.
- Free software only.

## Success criteria

- alice sends to bob from Thunderbird, and bob sees it in Thunderbird within seconds.
- Thunderbird shows no certificate warnings after the lab CA is trusted.
- An unauthenticated attempt to relay to an outside domain is rejected with `554 5.7.1 Relay access denied`.
- All checks in `90-verify.sh` and `mail_e2e_test.py` pass.
