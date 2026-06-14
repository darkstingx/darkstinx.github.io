---
title: HTB Silentium - Write-Up
date: 2026-06-10
categories:
  - Hack The Box
tags:
  - nginx
  - flowise
  - cve-2025-58434
  - cve-2025-59528
  - docker
  - gogs
  - cve-2025-8110
---

### Escaneo de puertos

Primero, realicé un escaneo rápido de todos los puertos con nmap:

<img width="1103" height="64" alt="image" src="https://github.com/user-attachments/assets/664c068d-150c-47d6-b388-d5abd5942a63" />


Luego realicé otro escaneo mas profundo sobre los puertos que encontré abiertos

<img width="1185" height="264" alt="2" src="https://github.com/user-attachments/assets/73b8c2eb-ce0c-416c-9fe8-39b2b02c6e0c" />


Encontramos una página web:

<img width="1914" height="694" alt="3" src="https://github.com/user-attachments/assets/9c99e043-630a-4581-8b37-a189722f2300" />


Hacemos fuzzing para buscar subdirectorios:

<img width="796" height="23" alt="4" src="https://github.com/user-attachments/assets/34ee4036-6298-4aaa-b8bb-61b86ad534cd" />


Encontramos una pagina para iniciar sesión
<img width="1394" height="768" alt="5" src="https://github.com/user-attachments/assets/0e2bb001-72a4-44d2-bc9d-8470aeb7f5bd" />


Probamos con un correo con un nombre de los que encontramos en la página principal, vemos que existe y vamos que la página de contraseña olvidada pide un token para resetear la contraseña.
Vamos a proceder a capturar el token


<img width="637" height="51" alt="6" src="https://github.com/user-attachments/assets/2f16b7c2-b3fb-4014-b6dd-73ad4c58a816" />


Cambiamos la contraseña usando el token que hemos capturado antes:

<img width="534" height="634" alt="7" src="https://github.com/user-attachments/assets/d0f6f0a6-057c-453f-b973-29e8c55dec88" />


Vemos que tenemos acceso a API Keys, creamos una para poder usarla en un futuro:

<img width="1776" height="662" alt="8" src="https://github.com/user-attachments/assets/0ecce18d-d02e-43c0-996b-c4c9322da410" />


Comprobamos que esa API Key es válida

<img width="622" height="53" alt="9" src="https://github.com/user-attachments/assets/00b8228b-a8f7-4c82-8219-5888a9d2d79c" />


Una vez comprobada que la API Key es válida lo que podemos hacer es abusar de ella, nos ponemos en escucha con netcat por el puesrto 4444 y ejecutamos los siguiente:

<img width="937" height="133" alt="10" src="https://github.com/user-attachments/assets/f77899bb-5935-4229-845d-c41c44236159" />


Ahora comprobamos que hemos recibido una shell en la terminal por la cual estabamos escuchando con netcat.

<img width="524" height="83" alt="11" src="https://github.com/user-attachments/assets/d8346541-7854-4520-bb5f-e7a0f97837b6" />


Vemos el archivo env que contiene credenciales interesantes

<img width="536" height="483" alt="12" src="https://github.com/user-attachments/assets/c14fe797-a5b4-4b55-9704-87acc0ef3167" />


Como antes hemos comprobado que tenia el puerto 22 abierto, vamos a probar a hacer ssh al usuario ben con la contraseña que acabamos de conseguir

<img width="242" height="32" alt="13" src="https://github.com/user-attachments/assets/d6984559-6ed1-4850-a107-40c1de29f96a" />


Una vez dentro, encontramos la flag de usuario

<img width="162" height="35" alt="14" src="https://github.com/user-attachments/assets/e3b659da-fde4-4f15-acf4-91e893e02a13" />


Buscamos los procesos activos del sistema y encontramos que se está ejecutando como root el proceso gogs web

<img width="619" height="72" alt="15" src="https://github.com/user-attachments/assets/106b2963-670b-4ed2-b7d8-ee710a485978" />


Hacemos un tunel ssh 

<img width="482" height="32" alt="16" src="https://github.com/user-attachments/assets/a5893e25-77ce-4381-9721-89081d4cf12b" />


Y encontramos la landing page de gogs, creamos un usuario

<img width="1071" height="679" alt="17" src="https://github.com/user-attachments/assets/11051d50-9f84-4ce8-9d80-544f553e61de" />


Esta versión sabemos que es vulnerable al CVE-2025-8110
<img width="443" height="22" alt="18" src="https://github.com/user-attachments/assets/dd09f882-cdb0-41b4-9b83-809827853ddb" />


Para ejecutar la vulnerabilidad, generamos un par de claves ssh

<img width="425" height="19" alt="19" src="https://github.com/user-attachments/assets/787fd95a-2c36-4fb4-a390-45c694c47121" />


Ejecutamos el script

<img width="436" height="104" alt="20" src="https://github.com/user-attachments/assets/70a8ca88-b2d2-4a4c-8930-b9252ffd09ea" />


Nos conectamos por ssh usando la key que hemos creado antes

<img width="558" height="34" alt="21" src="https://github.com/user-attachments/assets/b05d3445-0891-4995-937d-4c0d05f116ae" />


Y ya nos conectamos como root, hemos conseguido la elevación de privilegios y la flag de root
<img width="223" height="31" alt="22" src="https://github.com/user-attachments/assets/2106b5f7-990c-46c4-b939-d06656027fae" />
