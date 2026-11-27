# 07 · Thunderbird Client

## 1. Trust the lab CA

Thunderbird uses its own certificate store, not the operating system's.

1. Copy `out/maillab-ca.crt` to the client (shared folder, or `scp` from the host).
2. Thunderbird → **Settings → Privacy & Security → Certificates → Manage Certificates → Authorities → Import**.
3. Select `maillab-ca.crt` and tick **"Trust this CA to identify websites"**. Thunderbird uses this same trust bit for mail servers.

Skipping this step makes Thunderbird show a "security exception" dialog. Adding a per-server exception also works, but it
has to be repeated for every certificate change and teaches users to click through warnings.

## 2a. Automatic account setup

`provision/client.sh` installs `config/thunderbird/maillab.test.xml` into Thunderbird's `isp/` folder. On Windows the folder is
`C:\Program Files\Mozilla Thunderbird\isp\`.

1. **File → New → Existing Mail Account**
2. Name `Alice`, address `alice@maillab.test`, password from `out/maillab-credentials.txt`
3. Thunderbird shows *"Configuration found in Mozilla ISP database"* with IMAP 993 SSL/TLS and SMTP 587 STARTTLS → **Done**

## 2b. Manual account setup

| Setting | Incoming | Outgoing |
|---|---|---|
| Protocol | IMAP | SMTP |
| Server | mail.maillab.test | mail.maillab.test |
| Port | 993 | 587 |
| Connection security | SSL/TLS | STARTTLS |
| Authentication | Normal password | Normal password |
| Username | alice | alice |

"Normal password" is safe here because the connection is already encrypted before the password is sent.

## 3. Folders

Dovecot creates and subscribes **Drafts, Sent, Junk and Trash** automatically, with IMAP SPECIAL-USE flags, so Thunderbird
maps them correctly without any manual setup. Messages sent from Thunderbird are saved to the server's Sent folder and appear on
every device.

## 4. Second account and test

Add `bob@maillab.test` the same way (or on a second client VM). Test:

| Action | Expected |
|---|---|
| alice → bob, subject "Test 1" | Appears in bob's Inbox within a few seconds |
| bob replies | Appears in alice's Inbox, threaded with "Test 1" |
| alice → it-team@maillab.test | Delivered to both alice and bob (alias) |
| alice tries to send with From: bob@maillab.test | Rejected: `553 5.7.1 Sender address rejected: not owned by user alice` |
| Attachment 10 MB | Delivered |
| Attachment 30 MB | Rejected: message size exceeds the 25 MB limit |

## 5. POP3 option

To show POP3, add a third account with POP3 on 995 SSL/TLS and keep *"Leave messages on server"* ticked
(the default in the autoconfig file). The difference becomes clear: IMAP syncs folders and read state across clients, while POP3
downloads a copy.
