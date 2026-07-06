#!/usr/bin/env python3

import re
import subprocess
import sys
from datetime import datetime, timedelta
from collections import defaultdict, deque

# ---------------- CONFIG ----------------

PALABRAS_CLAVE = [
    "Failed password",
    "Invalid user",
    "authentication failure"
]

PATRON_IP = r"from (\d+\.\d+\.\d+\.\d+)"

VENTANA_SEGUNDOS = 60
UMBRAL = 5
BAN_MINUTOS = 10

# ---------------- ESTADO ----------------

intentos = defaultdict(deque)

# ---------------- CARGA DE BANS DESDE UFW ----------------

def cargar_bans_ufw():
    bans_cargados = {}

    try:
        salida = subprocess.check_output(
            ["ufw", "status", "numbered"],
            text=True
        )

        for linea in salida.splitlines():

            # Solo reglas de bloqueo SSH
            if "DENY IN" in linea and "22" in linea:

                ips = re.findall(r"\d+\.\d+\.\d+\.\d+", linea)

                if ips:
                    ip = ips[-1]
                    bans_cargados[ip] = datetime.now()

        return bans_cargados

    except Exception as e:
        print(f"❌ Error cargando bans desde UFW: {e}")
        return {}

# 🔥 IMPORTANTE: ahora se inicializa desde UFW
bans = cargar_bans_ufw()

# ---------------- FUNCIONES ----------------

def bloquear_ip(ip):
    print(f"🚨 BAN TEMPORAL: {ip}")

    subprocess.run([
        "ufw", "insert", "1",
        "deny", "in", "from", ip,
        "to", "any", "port", "22"
    ], check=False)

    bans[ip] = datetime.now()


def desbanear_ip(ip):
    print(f"🟢 DESBANEANDO: {ip}")

    try:
        salida = subprocess.check_output(
            ["ufw", "status", "numbered"],
            text=True
        )

        for linea in salida.splitlines():
            if ip in linea and "DENY IN" in linea:

                numero = linea.split("]")[0]
                numero = numero.replace("[", "").strip()

                subprocess.run([
                    "ufw", "--force", "delete", numero
                ], check=False)

                print(f"✅ Regla eliminada para {ip}")

        bans.pop(ip, None)

    except Exception as e:
        print(f"❌ Error desbaneando {ip}: {e}")


def listar_bans():
    print("\n=== IPS BLOQUEADAS (UFW) ===")

    try:
        salida = subprocess.check_output(
            ["ufw", "status", "numbered"],
            text=True
        )

        for linea in salida.splitlines():
            if "DENY IN" in linea:
                print(linea)

    except Exception as e:
        print(f"❌ Error listando UFW: {e}")


def limpiar_bans():
    ahora = datetime.now()

    for ip in list(bans.keys()):
        if ahora - bans[ip] > timedelta(minutes=BAN_MINUTOS):
            desbanear_ip(ip)


def limpiar_ventana(ip, ahora):
    ventana = intentos[ip]
    limite = ahora - timedelta(seconds=VENTANA_SEGUNDOS)

    while ventana and ventana[0] < limite:
        ventana.popleft()

# ---------------- CLI ----------------

if len(sys.argv) > 1:

    if sys.argv[1] == "--list":
        listar_bans()
        sys.exit(0)

    ip = sys.argv[1]
    desbanear_ip(ip)
    sys.exit(0)

# ---------------- MONITOR ----------------

print(f"🔍 Fail2Ban activo: {datetime.now()}")
print(f"📌 Bans cargados desde UFW: {list(bans.keys())}")

process = subprocess.Popen(
    ["journalctl", "-u", "ssh", "-f"],
    stdout=subprocess.PIPE,
    text=True
)

for linea in process.stdout:

    limpiar_bans()

    if not any(p in linea for p in PALABRAS_CLAVE):
        continue

    match = re.search(PATRON_IP, linea)
    if not match:
        continue

    ip = match.group(1)
    ahora = datetime.now()

    if ip in bans:
        continue

    intentos[ip].append(ahora)
    limpiar_ventana(ip, ahora)

    total = len(intentos[ip])

    print(f"{ip} -> {total} intentos (60s)")

    if total >= UMBRAL:
        bloquear_ip(ip)
