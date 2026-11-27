# 09 · Troubleshooting

## Where to look

| What | Command |
|---|---|
| Mail log (Postfix + Dovecot) | `sudo tail -f /var/log/mail.log` |
| Follow one message | `sudo grep <queue-id> /var/log/mail.log` |
| Queue | `mailq` / `sudo postqueue -p`; retry with `sudo postqueue -f` |
| Effective config | `postconf -n`, `doveconf -n` |
| Test auth | `sudo doveadm auth test alice` |
| Mailbox state | `sudo doveadm mailbox status -u bob all INBOX` |
| DNS | `dig @192.168.56.10 MX maillab.test`, `journalctl -u named` |
| Firewall and bans | `sudo ufw status`, `sudo fail2ban-client status dovecot` |

## Common problems

| Symptom | Cause | Fix |
|---|---|---|
| Thunderbird: *"Configuration could not be verified"* | Client cannot resolve `mail.maillab.test` | Set client DNS to 192.168.56.10; check with `nslookup mail.maillab.test` |
| Thunderbird: certificate warning | Lab CA not imported into Thunderbird's own store | [07](07-thunderbird-client.md) step 1 |
| `SASL authentication failed: generic failure` in mail.log | Postfix cannot reach Dovecot's auth socket | Check `ls -l /var/spool/postfix/private/auth`; restart dovecot, then postfix |
| `warning: connect to private/dovecot-lmtp: No such file` | Dovecot LMTP not running or the socket path is wrong | Install `dovecot-lmtpd`; check the `service lmtp` block |
| `lmtp ... User doesn't exist: bob@maillab.test` | Dovecot looked up the full address as a Unix user | `auth_username_format = %Ln` |
| `554 5.7.1 Relay access denied` when Thunderbird sends | Client is sending on 25 without authenticating | Use port 587 with STARTTLS and a password |
| `553 Sender address rejected: not owned by user` | From address does not match the login | Correct the identity in Thunderbird, or update `sender_login_maps` + `postmap` |
| Mail stuck in the queue with `Host or domain name not found` | Server not using its own BIND | Check `resolvectl status`; Postfix runs chrooted, so restart it to copy the new resolv.conf |
| `Connection refused` on 993 | UFW, or Dovecot failed to start | `sudo ss -ltnp \| grep 993`, `journalctl -u dovecot` |
| Dovecot fails to start: `ssl_cert: Can't open file` | Wrong path, or the `<` prefix is missing | `ssl_cert = </etc/ssl/maillab/...` (the `<` reads the file) |
| Ban on the host machine | fail2ban caught failed logins from 192.168.56.1 | `sudo fail2ban-client set dovecot unbanip 192.168.56.1` (the host is in `ignoreip` by default) |

## Reading a delivery line

```
postfix/lmtp[2211]: 4F2A11C0F3: to=<bob@maillab.test>, relay=mail.maillab.test[private/dovecot-lmtp],
  delay=0.12, delays=0.05/0.01/0.02/0.04, dsn=2.0.0, status=sent (250 2.0.0 <bob@maillab.test> kQd... Saved)
```

- `delays=a/b/c/d`: time in the queue before qmgr / waiting in qmgr / connection setup / transmission.
- `dsn=2.0.0` and `status=sent`: delivered. `4.x.x` means a temporary failure (it will retry). `5.x.x` means a permanent failure (it bounces).
