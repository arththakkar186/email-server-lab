# 08 · Testing

Three layers of tests:

| Layer | Runs | Tool |
|---|---|---|
| Static policy tests | Every push (CI), no VM needed | `tests/test_configs.py`, ShellCheck, `named-checkzone`, `postconf` |
| Server smoke tests | End of every `vagrant up` | `provision/90-verify.sh` |
| End-to-end | From client01 or the host | `scripts/mail_e2e_test.py`, Thunderbird |

## Test cases

| ID | Test | Command | Expected |
|---|---|---|---|
| E-01 | DNS MX | `dig +short MX maillab.test` | `10 mail.maillab.test.` |
| E-02 | DNS PTR | `dig +short -x 192.168.56.10` | `mail.maillab.test.` |
| E-03 | SMTP banner | `swaks --server mail.maillab.test --quit-after CONNECT` | `220 mail.maillab.test ESMTP` (no version disclosed) |
| E-04 | No AUTH before TLS | `swaks -s mail.maillab.test -p 587 --quit-after EHLO` | EHLO response lists `STARTTLS` but no `AUTH` |
| E-05 | STARTTLS certificate | `openssl s_client -starttls smtp -connect mail.maillab.test:587 -CAfile maillab-ca.crt` | `Verify return code: 0 (ok)`, TLSv1.3 |
| E-06 | IMAPS certificate | `openssl s_client -connect mail.maillab.test:993 -CAfile maillab-ca.crt` | `Verify return code: 0 (ok)` |
| E-07 | Plain IMAP closed | `nc -zv mail.maillab.test 143` | Connection refused |
| E-08 | Old TLS refused | `openssl s_client -connect mail.maillab.test:993 -tls1_1` | Handshake failure |
| E-09 | Authenticated send | `swaks -s mail.maillab.test -p 587 -tls -au alice -ap '<pw>' -f alice@maillab.test -t bob@maillab.test` | `250 2.0.0 Ok: queued as ...` |
| E-10 | Delivery | `sudo grep "to=<bob@maillab.test>" /var/log/mail.log \| tail -1` | `status=sent (250 2.0.0 <bob> ... Saved)` via `dovecot-lmtp` |
| E-11 | IMAP fetch | `mail_e2e_test.py` | Message found by Message-ID in bob's INBOX |
| E-12 | Received headers | Inspect in Thunderbird (View → Headers → All) | `with ESMTPSA (TLS1.3 ...)` |
| E-13 | Open relay refused | `swaks -s mail.maillab.test -p 25 -f x@example.net -t y@example.org` | `554 5.7.1 Relay access denied` |
| E-14 | Bad password | `swaks ... -au alice -ap wrong` | `535 5.7.8 Authentication failed` |
| E-15 | Spoofing between users | `swaks ... -au alice -f bob@maillab.test` | `553 5.7.1 Sender address rejected: not owned by user alice` |
| E-16 | Unknown recipient | `swaks ... -t nobody@maillab.test` | `550 5.1.1 User unknown` (rejected during the session, no bounce) |
| E-17 | Alias | Send to `it-team@maillab.test` | Copies in alice's and bob's Maildirs |
| E-18 | Size limit | 30 MB attachment | `552 5.3.4 Message size exceeds fixed limit` |
| E-19 | fail2ban | 6 bad IMAP logins from client01 | `fail2ban-client status dovecot` lists 192.168.56.20 as banned |
| E-20 | Thunderbird round trip | alice → bob → reply | Both directions delivered, Sent folders populated |

## Expected end-to-end output

This is what a fully passing run prints:

```text
$ python3 scripts/mail_e2e_test.py --ca out/maillab-ca.crt --sender alice --sender-pass *** --rcpt bob --rcpt-pass ***
1. DNS
  [PASS] mail.maillab.test resolves - 192.168.56.10
2. Submission (587, STARTTLS + AUTH)
  [PASS] AUTH not offered before STARTTLS
  [PASS] STARTTLS negotiated - TLSv1.3
  [PASS] SMTP AUTH accepted
  [PASS] message accepted for delivery
3. Retrieval (993, IMAPS)
  [PASS] IMAP login
  [PASS] message arrived in INBOX - waited up to 30s
4. Headers
  [PASS] Received header records TLS
  [PASS] Received header shows authenticated submission (ESMTPSA)
5. Negative tests
  [PASS] bad password rejected
  [PASS] open relay refused - 554 5.7.1 <victim@example.org>: Relay access denied
  [PASS] plain-text IMAP 143 closed

12/12 checks passed
```
