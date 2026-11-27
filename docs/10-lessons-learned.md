# 10 · Lessons Learned

## Key takeaways

1. **DNS first.** Many "mail is broken" problems are really DNS problems: the client cannot resolve the
   server, or the MX points at a name with no A record. Check with `dig` before touching Postfix.
2. **Logs give the answer.** `/var/log/mail.log` names the failing component (smtpd, lmtp, auth) and gives a reason
   code. Being able to read a delivery line is the most useful troubleshooting skill for mail.
3. **Snapshots.** A VM snapshot after every working step makes it safe to experiment.
4. **TLS is about trust, not only encryption.** A self-signed certificate encrypts traffic just as well, but every
   client warns about it. A CA that clients trust once makes the warnings go away, which is how real PKI works.
5. **Authentication belongs on 587.** Separating server-to-server delivery (25) from user submission (587) keeps
   the relay rules simple and safe.

## What I would do differently now (2026)

| Then | Now | Why |
|---|---|---|
| Manual, step-by-step procedure | Vagrant + shell scripts + CI | Repeatable in minutes, and every change is reviewed and tested |
| System users | Dovecot virtual users (passwd-file or SQL) under one `vmail` UID | Mail accounts are separate from OS accounts, which scales better and is safer |
| Self-run CA | ACME (Let's Encrypt) on a real domain | Automatic renewal, trusted by every client |
| No content filtering | Rspamd (spam + DKIM signing + DMARC) | Expected baseline for any internet-facing server |
| Password logins | OAuth2 / modern auth where clients support it, plus MFA through an identity provider | The same direction Microsoft 365 took when it turned off Basic Auth for Exchange Online |
| Single VM | Separate MX gateway and mailbox server, plus backups | Smaller blast radius, easier maintenance |

The password row links directly to my later identity work: the move from passwords on mail protocols to
token-based modern authentication is what Conditional Access and MFA policies in Entra ID enforce for Exchange Online.
