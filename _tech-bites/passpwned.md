# PassPwned

Herramienta de línea de comandos en Python para comprobar si una contraseña ha sido comprometida en filtraciones conocidas, usando la API de [Have I Been Pwned](https://haveibeenpwned.com/) (HIBP) mediante el modelo **k-Anonymity**, y para generar contraseñas seguras. Interfaz de terminal interactiva construida con [Rich](https://github.com/Textualize/rich).

## Funcionalidades

- **Comprobación de contraseñas comprometidas** contra la HIBP Range API, sin enviar nunca la contraseña ni su hash completo (ver explicación de k-Anonymity más abajo).
- **Clasificación del nivel de riesgo** según el número de apariciones en filtraciones:
  - 🔴 **Crítico**: ≥ 100.000 apariciones
  - 🟠 **Alto**: ≥ 1.000 apariciones
  - 🟡 **Medio**: ≥ 100 apariciones
  - 🟡 **Bajo**: < 100 apariciones
- **Generador de contraseñas criptográficamente seguras** (`secrets`, no `random`), con longitud configurable (mínimo 12, por defecto 20) y símbolos especiales opcionales. Garantiza que la contraseña generada incluya al menos una mayúscula, una minúscula, un número y (si se activa) un símbolo.
- **Verificación automática de la contraseña generada**: tras generarla, ofrece comprobarla también contra HIBP.
- Estimación aproximada de entropía de la contraseña generada.
- Manejo de errores de red (sin conexión, timeout, error HTTP) con mensajes claros.
- Interfaz de terminal completa con paneles, tablas y colores mediante Rich; no requiere argumentos por línea de comandos, todo el flujo es interactivo.

## ¿Cómo funciona el k-Anonymity?

1. Se calcula localmente el hash SHA-1 de la contraseña.
2. Solo se envían a la API de HIBP los **primeros 5 caracteres** de ese hash.
3. HIBP devuelve todos los sufijos de hash que comparten ese prefijo (normalmente varios cientos).
4. La comparación del sufijo completo se hace **en local**, por lo que la contraseña real ni su hash completo salen nunca de tu máquina.

## Instalación

```bash
git clone https://github.com/darkstinx/passpwned.git
cd passpwned
pip install requests rich
```

### Dependencias

- `requests`
- `rich`

(El resto de módulos usados — `hashlib`, `secrets`, `string`, `sys`, `time` — son de la librería estándar de Python.)

## Uso

```bash
python passpwned.py
```

La herramienta lanza un menú interactivo:

1. Te pide la contraseña a comprobar (entrada oculta, sin eco en pantalla).
2. Consulta HIBP usando k-Anonymity y muestra el resultado:
   - Si **no está filtrada**: panel de confirmación + tabla de buenas prácticas (2FA, gestor de contraseñas, no reutilización, etc.).
   - Si **está filtrada**: panel de alerta con el número de apariciones y el nivel de riesgo, y un submenú para:
     - Generar una contraseña segura nueva
     - Comprobar otra contraseña
     - Salir
3. Si generas una contraseña nueva, puedes verificarla también contra HIBP en el mismo flujo.

## Motivación

Proyecto creado como parte de mi transición hacia ciberseguridad, para practicar el consumo de APIs de seguridad reales y buenas prácticas de manejo de credenciales (nunca transmitir datos sensibles en claro, minimizar la superficie expuesta a terceros, uso de `secrets` en vez de `random` para generación criptográfica).

## Aviso

La herramienta consulta un servicio externo (HIBP). No almacena ni registra en ningún momento las contraseñas comprobadas o generadas.

## Licencia

MIT
