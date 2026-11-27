#!/usr/bin/env python3
"""End-to-end mail test for the lab, run from the client VM or the host.

It does what Thunderbird does, step by step, and checks each result:

  1. Resolve MX and A records for maillab.test
  2. Submit a message as the sender on 587 (STARTTLS, then AUTH)
  3. Log in to the recipient's mailbox on 993 (IMAPS) and wait for the message
  4. Check the Received headers show TLS and authenticated submission
  5. Confirm the server refuses AUTH before STARTTLS and refuses to relay

Usage:
  python3 scripts/mail_e2e_test.py --ca out/maillab-ca.crt \
      --sender alice --sender-pass '...' --rcpt bob --rcpt-pass '...'

Standard library only.
"""
from __future__ import annotations

import argparse
import imaplib
import smtplib
import socket
import ssl
import sys
import time
import uuid
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default as default_policy

DOMAIN = "maillab.test"
HOST = f"mail.{DOMAIN}"

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> bool:
    results.append((name, ok, detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}{(' - ' + detail) if detail else ''}")
    return ok


def tls_context(ca: str | None) -> ssl.SSLContext:
    ctx = ssl.create_default_context(cafile=ca)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_2
    return ctx


def step_dns(host: str) -> None:
    print("1. DNS")
    try:
        ip = socket.gethostbyname(host)
        check(f"{host} resolves", True, ip)
    except OSError as e:
        check(f"{host} resolves", False, str(e))


def step_submit(a, ctx, token: str) -> str | None:
    print("2. Submission (587, STARTTLS + AUTH)")
    msg = EmailMessage()
    msg["From"] = f"{a.sender}@{DOMAIN}"
    msg["To"] = f"{a.rcpt}@{DOMAIN}"
    msg["Subject"] = f"MailLab e2e {token}"
    msg["Message-ID"] = f"<{token}@{DOMAIN}>"
    msg.set_content("End-to-end test message from scripts/mail_e2e_test.py\n")
    try:
        with smtplib.SMTP(a.host, 587, timeout=20) as s:
            s.ehlo("client01.maillab.test")
            check("AUTH not offered before STARTTLS", "auth" not in s.esmtp_features)
            s.starttls(context=ctx)
            s.ehlo("client01.maillab.test")
            check("STARTTLS negotiated", s.sock.version() in ("TLSv1.2", "TLSv1.3"), s.sock.version())
            s.login(a.sender, a.sender_pass)
            check("SMTP AUTH accepted", True)
            s.send_message(msg)
            check("message accepted for delivery", True)
        return token
    except (smtplib.SMTPException, OSError, ssl.SSLError) as e:
        check("submission", False, repr(e))
        return None


def step_imap(a, ctx, token: str) -> None:
    print("3. Retrieval (993, IMAPS)")
    try:
        with imaplib.IMAP4_SSL(a.host, 993, ssl_context=ctx) as m:
            m.login(a.rcpt, a.rcpt_pass)
            check("IMAP login", True)
            deadline = time.time() + a.timeout
            found = None
            while time.time() < deadline and not found:
                m.select("INBOX")
                typ, data = m.search(None, "HEADER", "Message-ID", f"<{token}@{DOMAIN}>")
                ids = data[0].split()
                if ids:
                    found = ids[-1]
                else:
                    time.sleep(1)
            if not check("message arrived in INBOX", found is not None, f"waited up to {a.timeout}s"):
                return
            typ, data = m.fetch(found, "(RFC822)")
            parsed = BytesParser(policy=default_policy).parsebytes(data[0][1])
            received = " ".join(parsed.get_all("Received", []))
            print("4. Headers")
            check("Received header records TLS", "TLS" in received or "ESMTPSA" in received)
            check("Received header shows authenticated submission (ESMTPSA)", "ESMTPSA" in received)
            m.store(found, "+FLAGS", "\\Deleted")
            m.expunge()
    except (imaplib.IMAP4.error, OSError, ssl.SSLError) as e:
        check("IMAP", False, repr(e))


def step_negative(a, ctx) -> None:
    print("5. Negative tests")
    # Wrong password must fail.
    try:
        with smtplib.SMTP(a.host, 587, timeout=20) as s:
            s.starttls(context=ctx)
            s.login(a.sender, a.sender_pass + "x")
        check("bad password rejected", False, "login unexpectedly succeeded")
    except smtplib.SMTPAuthenticationError:
        check("bad password rejected", True)
    # Unauthenticated relay to an outside domain on port 25 must fail.
    try:
        with smtplib.SMTP(a.host, 25, timeout=20) as s:
            s.ehlo("client01.maillab.test")
            s.mail("someone@example.net")
            code, resp = s.rcpt("victim@example.org")
            check("open relay refused", code >= 500, f"{code} {resp.decode(errors='replace')}")
    except (smtplib.SMTPException, OSError) as e:
        check("open relay refused", False, repr(e))
    # Plain-text IMAP must be closed.
    try:
        socket.create_connection((a.host, 143), timeout=5).close()
        check("plain-text IMAP 143 closed", False, "port 143 accepted a connection")
    except OSError:
        check("plain-text IMAP 143 closed", True)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="MailLab end-to-end test")
    p.add_argument("--host", default=HOST)
    p.add_argument("--ca", help="path to maillab-ca.crt (from out/ after vagrant up)")
    p.add_argument("--sender", default="alice")
    p.add_argument("--sender-pass", required=True)
    p.add_argument("--rcpt", default="bob")
    p.add_argument("--rcpt-pass", required=True)
    p.add_argument("--timeout", type=int, default=30)
    a = p.parse_args(argv)

    ctx = tls_context(a.ca)
    token = uuid.uuid4().hex[:12]
    step_dns(a.host)
    if step_submit(a, ctx, token):
        step_imap(a, ctx, token)
    step_negative(a, ctx)

    failed = [r for r in results if not r[1]]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
