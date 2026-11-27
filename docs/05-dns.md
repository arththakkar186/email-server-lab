# 05 · DNS Design

Email depends on DNS more than any other common service does. Senders find a domain's mail server through the MX
record, and receivers judge senders partly by their PTR, SPF and DMARC records.

## Zones

| Zone | Type | File |
|---|---|---|
| `maillab.test` | Primary (master) | `config/bind/db.maillab.test` |
| `56.168.192.in-addr.arpa` | Primary (master) | `config/bind/db.192.168.56` |

`.test` is reserved by RFC 2606 and will never be delegated on the internet, so the lab cannot collide with or leak to a real domain.

## Records and why each one exists

| Record | Value | Purpose |
|---|---|---|
| `SOA` | ns1, serial `YYYYMMDDnn` | Zone authority; the serial must increase on every edit or secondaries keep old data |
| `NS` | ns1.maillab.test | Which server is authoritative |
| `MX 10` | mail.maillab.test | **Where mail for @maillab.test is delivered.** Without it, senders fall back to the A record of the bare domain |
| `A mail` | 192.168.56.10 | Address of the mail server. The MX target **must** be an A/AAAA name, not a CNAME (RFC 2181 §10.3) |
| `PTR 10` | mail.maillab.test | Reverse lookup. Receiving servers check that the PTR exists and matches the HELO name (forward-confirmed reverse DNS) |
| `CNAME imap, smtp, autoconfig` | mail | Hostnames mail clients guess during auto-setup |
| `TXT SPF` | `v=spf1 mx -all` | Only the domain's MX hosts may send as @maillab.test; reject everything else |
| `TXT _dmarc` | `v=DMARC1; p=quarantine; rua=...` | What receivers should do when SPF/DKIM fail, and where to send reports |

A unit test (`tests/test_configs.py`) checks that the MX target has an A record, that forward and reverse lookups agree, and that
the serial is in date format.

## Resolver behaviour

- `recursion yes` but `allow-recursion { lab; }`, so only 127.0.0.0/8 and 192.168.56.0/24 can use the server
  as a resolver. An open resolver can be abused for DNS amplification attacks.
- Queries outside `maillab.test` are forwarded to the VirtualBox NAT resolver (10.0.2.3).
- `version "not disclosed"` hides the BIND version from `dig CH TXT version.bind`.
- `allow-transfer { none; }` stops anyone from copying the whole zone with AXFR.

## Lookup examples

```text
$ dig MX maillab.test +noall +answer
maillab.test.     3600  IN  MX  10 mail.maillab.test.

$ dig -x 192.168.56.10 +short
mail.maillab.test.

$ dig TXT maillab.test +short
"v=spf1 mx -all"
```

## DKIM (extension)

DKIM was not part of the original lab. With OpenDKIM it would add a `mail._domainkey` TXT record holding the
public key, and Postfix would sign outgoing mail through a milter. Together, SPF, DKIM and DMARC are what large mail
providers now require from bulk senders.
