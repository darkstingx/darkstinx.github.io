
# SSH Brute-Force Detector & Auto-Ban

Herramienta en Python para monitorizar en tiempo real los logs de autenticación SSH, detectar patrones de fuerza bruta y bloquear automáticamente las IPs atacantes mediante UFW. Sincroniza su estado con las reglas de UFW ya existentes, por lo que es resistente a reinicios del propio script.

## Funcionalidades

- **Monitorización en tiempo real** de los logs SSH vía `journalctl -u ssh -f`, sin necesidad de parsear ficheros de log estáticos.
- **Detección de intentos de login fallidos**, identificando las líneas que contienen:
  - `Failed password`
  - `Invalid user`
  - `authentication failure`
- **Extracción automática de la IP de origen** mediante expresión regular sobre la línea de log.
- **Ventana deslizante de intentos**: cuenta los intentos por IP en los últimos 60 segundos (configurable) usando una `deque`, descartando los intentos antiguos que quedan fuera de la ventana.
- **Bloqueo automático (ban) vía UFW**: si una IP supera el umbral de intentos (5 por defecto) dentro de la ventana, se inserta una regla `ufw deny` en la posición 1 para el puerto 22.
- **Desbaneo automático tras un tiempo configurable** (10 minutos por defecto): el propio script revisa periódicamente los bans activos y elimina la regla de UFW correspondiente cuando expira.
- **Sincronización de estado con UFW al arrancar**: al iniciar, el script lee las reglas `DENY IN` ya existentes en UFW para el puerto 22 y reconstruye su lista interna de IPs baneadas. Esto evita que, tras un reinicio del script (crash, reboot, `systemctl restart`), se pierda el registro de IPs ya bloqueadas y la regla quede huérfana en UFW para siempre.
- **Modo CLI** para gestión manual, sin necesidad de tocar UFW directamente:
  - Listar IPs bloqueadas actualmente
  - Desbanear una IP concreta a mano

## Cómo funciona

1. Al arrancar, llama a `cargar_bans_ufw()`, que ejecuta `ufw status numbered` y reconstruye el diccionario de IPs ya baneadas relacionadas con el puerto 22.
2. Lanza `journalctl -u ssh -f` como subproceso y procesa cada línea nueva que llega.
3. Si la línea contiene alguna de las palabras clave de fallo de autenticación, extrae la IP con la regex `from (\d+\.\d+\.\d+\.\d+)`.
4. Si la IP no está ya baneada, registra el intento con su timestamp y limpia los intentos fuera de la ventana de 60 segundos.
5. Si el número de intentos dentro de la ventana alcanza el umbral, ejecuta `ufw insert 1 deny in from <ip> to any port 22` y registra el ban con la hora actual.
6. En cada iteración del bucle también comprueba si algún ban ha superado los `BAN_MINUTOS` configurados, y si es así, localiza la regla en `ufw status numbered` y la elimina con `ufw --force delete <número>`.

## Instalación

```bash
git clone https://github.com/darkstinx/ssh-log-analyzer.git
cd ssh-log-analyzer
```

### Requisitos

- Python 3 (solo librería estándar: `re`, `subprocess`, `sys`, `datetime`, `collections` — no requiere dependencias externas de pip).
- **UFW** instalado y activo en el sistema.
- **systemd** con el servicio `ssh` registrado en journald (`journalctl -u ssh`).
- Ejecutar con permisos suficientes para invocar `ufw` (normalmente `sudo` o como root), ya que el script inserta y elimina reglas de firewall.

## Uso

### Modo monitor (por defecto)

```bash
sudo python3 RecolectLog.py
```

Arranca la monitorización en tiempo real. Al iniciar, muestra las IPs ya baneadas que ha encontrado en UFW y, a partir de ahí, imprime cada intento fallido detectado y cada ban/desbaneo que se ejecuta.

### Listar IPs bloqueadas

```bash
sudo python3 RecolectLog.py --list
```

### Desbanear una IP manualmente

```bash
sudo python3 RecolectLog.py 203.0.113.45
```

## Configuración

Los parámetros de detección están definidos como constantes al inicio del script y se pueden ajustar directamente:

```python
VENTANA_SEGUNDOS = 60   # ventana de tiempo para contar intentos
UMBRAL = 5              # nº de intentos que dispara el ban
BAN_MINUTOS = 10        # duración del ban antes de desbanear automáticamente
```

## Motivación

Proyecto creado como parte de mi transición hacia ciberseguridad, orientado a la parte de detección y respuesta que se trabaja en un SOC: identificar patrones de fuerza bruta sobre un servicio expuesto (SSH) a partir de logs en tiempo real, y automatizar una respuesta de contención (bloqueo temporal) manteniendo la consistencia del estado del sistema tras reinicios.

## Aviso

Este script modifica las reglas de firewall del sistema (UFW) de forma automática. Pruébalo primero en un entorno controlado (VM, laboratorio) antes de usarlo en un sistema en producción, y asegúrate de no bloquear tu propia IP de administración.

## Licencia

MIT
