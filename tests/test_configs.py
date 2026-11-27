"""Static checks on the committed configuration. They run in CI without any VM.

They encode the security rules of the design, so a careless edit (for example,
adding the lab subnet to mynetworks, which would create an open relay) fails the build.
"""
from __future__ import annotations

import ipaddress
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config"


def postfix_params(path: Path) -> dict:
    """Parse main.cf, joining indented continuation lines."""
    params, key = {}, None
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        if line[0].isspace() and key:
            params[key] += " " + line.strip()
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        params[key] = val.strip()
    return params


def master_service(path: Path, name: str) -> list[str]:
    lines = path.read_text().splitlines()
    for i, l in enumerate(lines):
        if re.match(rf"^{name}\s+inet\b", l):
            opts = []
            for nxt in lines[i + 1:]:
                if nxt.startswith("  -o"):
                    opts.append(nxt.strip()[3:].strip())
                else:
                    break
            return opts
    raise AssertionError(f"service {name} not found in master.cf")


def dovecot_value(text: str, key: str) -> str | None:
    m = re.search(rf"^\s*{key}\s*=\s*(.+)$", text, re.M)
    return m.group(1).strip() if m else None


def restrictions(value: str) -> list[str]:
    return [x.strip() for x in value.replace("\n", " ").split(",") if x.strip()]


class TestPostfix(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = postfix_params(CFG / "postfix" / "main.cf")

    def test_mynetworks_is_loopback_only(self):
        for net in self.p["mynetworks"].split():
            self.assertTrue(ipaddress.ip_network(net).is_loopback,
                            f"{net} in mynetworks would let it relay without authentication")

    def test_relay_restrictions_end_in_reject(self):
        r = restrictions(self.p["smtpd_relay_restrictions"])
        self.assertEqual(r[-1], "reject_unauth_destination")
        self.assertIn("permit_sasl_authenticated", r)
        self.assertNotIn("permit", r[:-1], "a bare 'permit' before the reject makes an open relay")

    def test_recipient_restrictions_reject_unlisted(self):
        r = restrictions(self.p["smtpd_recipient_restrictions"])
        self.assertIn("reject_unlisted_recipient", r)
        self.assertIn("reject_unauth_destination", r)

    def test_tls_disallows_legacy_protocols(self):
        for key in ("smtpd_tls_protocols", "smtpd_tls_mandatory_protocols"):
            for bad in ("!SSLv2", "!SSLv3", "!TLSv1", "!TLSv1.1"):
                self.assertIn(bad, self.p[key], f"{key} must exclude {bad[1:]}")

    def test_sasl_not_global(self):
        self.assertEqual(self.p["smtpd_sasl_auth_enable"], "no",
                         "AUTH belongs on submission only, not on port 25")

    def test_vrfy_disabled_and_helo_required(self):
        self.assertEqual(self.p["disable_vrfy_command"], "yes")
        self.assertEqual(self.p["smtpd_helo_required"], "yes")

    def test_delivery_via_dovecot_lmtp(self):
        self.assertEqual(self.p["mailbox_transport"], "lmtp:unix:private/dovecot-lmtp")

    def test_submission_service(self):
        opts = dict(o.split("=", 1) for o in master_service(CFG / "postfix" / "master.cf", "submission"))
        self.assertEqual(opts["smtpd_tls_security_level"], "encrypt")
        self.assertEqual(opts["smtpd_sasl_auth_enable"], "yes")
        self.assertEqual(opts["smtpd_tls_auth_only"], "yes")
        self.assertEqual(opts["smtpd_relay_restrictions"], "permit_sasl_authenticated,reject")
        self.assertIn("reject_sender_login_mismatch", opts["smtpd_sender_restrictions"])


class TestDovecot(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.t = (CFG / "dovecot" / "99-maillab.conf").read_text()

    def test_tls_required(self):
        self.assertEqual(dovecot_value(self.t, "ssl"), "required")
        self.assertEqual(dovecot_value(self.t, "disable_plaintext_auth"), "yes")
        self.assertEqual(dovecot_value(self.t, "ssl_min_protocol"), "TLSv1.2")

    def test_plaintext_listeners_disabled(self):
        for proto in ("imap", "pop3"):
            block = re.search(rf"inet_listener {proto} \{{(.*?)\}}", self.t, re.S).group(1)
            self.assertIn("port = 0", block, f"plain-text {proto} listener must be disabled")

    def test_sockets_match_postfix(self):
        p = postfix_params(CFG / "postfix" / "main.cf")
        self.assertIn(f"/var/spool/postfix/{p['smtpd_sasl_path']}", self.t)
        self.assertIn("/var/spool/postfix/private/dovecot-lmtp", self.t)

    def test_username_format_strips_domain(self):
        self.assertEqual(dovecot_value(self.t, "auth_username_format"), "%Ln")


class TestDNS(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fwd = (CFG / "bind" / "db.maillab.test").read_text()
        cls.rev = (CFG / "bind" / "db.192.168.56").read_text()

    def records(self, text, rtype):
        out = {}
        for line in text.splitlines():
            line = line.split(";", 1)[0]
            m = re.match(rf"^(\S+)\s+IN\s+{rtype}\s+(.+)$", line)
            if m:
                out[m.group(1)] = m.group(2).strip()
        return out

    def test_serial_format(self):
        for text in (self.fwd, self.rev):
            serial = re.search(r"(\d{10})\s*;\s*serial", text).group(1)
            self.assertRegex(serial, r"^20\d{2}(0[1-9]|1[0-2])(0[1-9]|[12]\d|3[01])\d{2}$")

    def test_mx_target_has_a_record(self):
        mx = self.records(self.fwd, "MX")["@"]
        target = mx.split()[1].rstrip(".").split(".")[0]
        self.assertIn(target, self.records(self.fwd, "A"), "MX must point at a name with an A record, not a CNAME")

    def test_forward_and_reverse_agree(self):
        a = self.records(self.fwd, "A")
        ptr = self.records(self.rev, "PTR")
        mail_ip = a["mail"]
        self.assertEqual(ptr[mail_ip.split(".")[-1]], "mail.maillab.test.", "FCrDNS: PTR must match the A record")

    def test_uses_reserved_tld(self):
        self.assertNotRegex(self.fwd, r"\b(com|net|org|ca)\.\s", "lab zone must stay on the reserved .test TLD")


class TestScripts(unittest.TestCase):
    def test_strict_mode(self):
        for sh in (ROOT / "provision").glob("*.sh"):
            self.assertIn("set -euo pipefail", sh.read_text(), sh.name)

    def test_no_hardcoded_passwords(self):
        for path in list((ROOT / "provision").glob("*.sh")) + list(CFG.rglob("*")):
            if path.is_file():
                text = path.read_text(errors="ignore")
                self.assertNotRegex(text, r"chpasswd\s*<<<|password\s*=\s*['\"]\w+", path.name)

    def test_thunderbird_autoconfig_matches_server(self):
        xml = (CFG / "thunderbird" / "maillab.test.xml").read_text()
        self.assertIn("<port>993</port>", xml)
        self.assertIn("<port>587</port>", xml)
        self.assertIn("<socketType>STARTTLS</socketType>", xml)
        self.assertNotIn("<socketType>plain</socketType>", xml)


if __name__ == "__main__":
    unittest.main()
