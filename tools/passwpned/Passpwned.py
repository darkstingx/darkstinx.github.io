#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║        HIBP Password Checker v1.0            ║
║   Have I Been Pwned - Password API           ║
║   Método k-Anonymity (SHA-1 parcial)         ║
╚══════════════════════════════════════════════╝
"""

import hashlib
import secrets
import string
import sys
import time

import requests
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich import box

# ──────────────────────────────────────────────
# Configuración global
# ──────────────────────────────────────────────
console = Console()

HIBP_API_URL = "https://api.pwnedpasswords.com/range/"
HIBP_HEADERS = {"User-Agent": "HIBP-Password-Checker-Personal/1.0"}

# Paleta de colores
COLOR_OK      = "bold green"
COLOR_WARN    = "bold yellow"
COLOR_DANGER  = "bold red"
COLOR_INFO    = "bold cyan"
COLOR_DIM     = "dim white"
COLOR_TITLE   = "bold magenta"


# ──────────────────────────────────────────────
# Utilidades de consola
# ──────────────────────────────────────────────
def limpiar_pantalla():
    console.clear()


def mostrar_banner():
    banner = Text()
    banner.append("\n  🔐 HIBP Password Checker\n", style="bold magenta")
    banner.append("  Have I Been Pwned · k-Anonymity API\n", style=COLOR_DIM)
    console.print(Panel(banner, border_style="magenta", padding=(0, 2)))
    console.print()


def separador(titulo: str = ""):
    console.print(Rule(titulo, style="magenta"))


def pausa(segundos: float = 1.2):
    time.sleep(segundos)


# ──────────────────────────────────────────────
# Lógica HIBP
# ──────────────────────────────────────────────
def hash_sha1(password: str) -> str:
    """Devuelve el hash SHA-1 en mayúsculas de la contraseña."""
    return hashlib.sha1(password.encode("utf-8")).hexdigest().upper()


def consultar_hibp(prefijo_hash: str) -> str:
    """
    Llama a la HIBP Range API con los primeros 5 caracteres del hash.
    Devuelve el cuerpo de la respuesta (sufijos + conteos).
    Lanza requests.HTTPError si hay problema.
    """
    url = HIBP_API_URL + prefijo_hash
    respuesta = requests.get(url, headers=HIBP_HEADERS, timeout=10)
    respuesta.raise_for_status()
    return respuesta.text


def buscar_sufijo(sufijo_hash: str, datos_api: str) -> int:
    """
    Busca el sufijo del hash en la respuesta de la API.
    Devuelve el número de filtraciones encontradas (0 si no aparece).
    """
    for linea in datos_api.splitlines():
        partes = linea.split(":")
        if len(partes) == 2:
            suf, conteo = partes
            if suf.strip() == sufijo_hash:
                return int(conteo.strip())
    return 0


def verificar_contrasena(password: str) -> tuple[bool, int]:
    """
    Comprueba si la contraseña está filtrada usando k-Anonymity.
    Devuelve (filtrada: bool, veces: int).
    """
    hash_completo = hash_sha1(password)
    prefijo  = hash_completo[:5]
    sufijo   = hash_completo[5:]

    with console.status("[cyan]Consultando HIBP API...[/cyan]", spinner="dots"):
        datos = consultar_hibp(prefijo)

    veces = buscar_sufijo(sufijo, datos)
    return (veces > 0, veces)


# ──────────────────────────────────────────────
# Mostrar resultados
# ──────────────────────────────────────────────
def mostrar_resultado_seguro():
    separador()
    console.print()
    console.print(
        Panel(
            Text.assemble(
                ("  ✅  ", "bold green"),
                ("¡Contraseña NO encontrada en filtraciones conocidas!\n\n", COLOR_OK),
                ("  Tu contraseña no aparece en ninguna base de datos comprometida\n", COLOR_DIM),
                ("  registrada por Have I Been Pwned.\n\n", COLOR_DIM),
                ("  🛡️  Estado: ", "white"),
                ("SEGURA\n", COLOR_OK),
            ),
            border_style="green",
            padding=(1, 2),
        )
    )
    console.print()

    # Consejos adicionales
    tabla = Table(
        title="💡 Buenas prácticas para mantenerla segura",
        box=box.ROUNDED,
        border_style="dim green",
        show_header=False,
        padding=(0, 1),
    )
    tabla.add_column("", style="green")
    tabla.add_column("", style="white")
    tabla.add_row("•", "No reutilices esta contraseña en otros servicios")
    tabla.add_row("•", "Activa la autenticación en dos factores (2FA)")
    tabla.add_row("•", "Guárdala en un gestor de contraseñas")
    tabla.add_row("•", "Cámbiala periódicamente (cada 6-12 meses)")
    console.print(tabla)
    console.print()


def mostrar_resultado_filtrado(veces: int):
    separador()
    console.print()

    # Determinar nivel de riesgo según frecuencia
    if veces >= 100_000:
        nivel      = "🔴 CRÍTICO"
        color_nivel = COLOR_DANGER
        mensaje    = "Esta contraseña es extremadamente común. Cámbiala de inmediato."
    elif veces >= 1_000:
        nivel      = "🟠 ALTO"
        color_nivel = "bold orange1"
        mensaje    = "Aparece miles de veces. Es un riesgo serio."
    elif veces >= 100:
        nivel      = "🟡 MEDIO"
        color_nivel = COLOR_WARN
        mensaje    = "Ha aparecido en varias filtraciones. Cámbiala pronto."
    else:
        nivel      = "🟡 BAJO"
        color_nivel = COLOR_WARN
        mensaje    = "Aparece en algunas filtraciones. Recomendamos cambiarla."

    # Panel principal
    console.print(
        Panel(
            Text.assemble(
                ("  ⚠️   ¡CONTRASEÑA FILTRADA!\n\n", COLOR_DANGER),
                ("  Tu contraseña ha aparecido en bases de datos de contraseñas\n", COLOR_DIM),
                ("  comprometidas registradas por Have I Been Pwned.\n\n", COLOR_DIM),
                ("  📊 Apariciones en filtraciones: ", "white"),
                (f"{veces:,}\n".replace(",", "."), COLOR_DANGER),
                ("  ⚡ Nivel de riesgo:             ", "white"),
                (f"{nivel}\n\n", color_nivel),
                ("  " + mensaje, COLOR_WARN),
            ),
            border_style="red",
            padding=(1, 2),
        )
    )
    console.print()

    # Tabla de información detallada
    tabla_info = Table(
        title="📋 Detalle de la filtración",
        box=box.ROUNDED,
        border_style="dim red",
        show_header=True,
        header_style="bold red",
    )
    tabla_info.add_column("Campo", style="white", min_width=22)
    tabla_info.add_column("Valor", style="yellow")

    tabla_info.add_row("Apariciones confirmadas", f"{veces:,}".replace(",", "."))
    tabla_info.add_row("Fuente de datos",         "Have I Been Pwned (hibp)")
    tabla_info.add_row("Método de consulta",       "k-Anonymity SHA-1 (seguro)")
    tabla_info.add_row("Estado",                   f"[bold red]COMPROMETIDA[/bold red]")
    tabla_info.add_row("Nivel de riesgo",           f"[{color_nivel}]{nivel}[/{color_nivel}]")

    console.print(tabla_info)
    console.print()


# ──────────────────────────────────────────────
# Generador de contraseñas seguras
# ──────────────────────────────────────────────
def generar_contrasena(longitud: int, usar_simbolos: bool) -> str:
    """Genera una contraseña criptográficamente segura."""
    caracteres = string.ascii_letters + string.digits
    if usar_simbolos:
        caracteres += "!@#$%^&*()-_=+[]{}|;:,.<>?"

    while True:
        password = "".join(secrets.choice(caracteres) for _ in range(longitud))

        # Garantizar al menos un carácter de cada tipo requerido
        tiene_mayus  = any(c.isupper() for c in password)
        tiene_minus  = any(c.islower() for c in password)
        tiene_numero = any(c.isdigit() for c in password)
        tiene_simbol = any(c in "!@#$%^&*()-_=+[]{}|;:,.<>?" for c in password) if usar_simbolos else True

        if tiene_mayus and tiene_minus and tiene_numero and tiene_simbol:
            return password


def flujo_generar_contrasena():
    """Submenú interactivo para generar una contraseña segura."""
    separador("Generador de contraseñas")
    console.print()

    longitud = IntPrompt.ask(
        "  [cyan]Longitud de la contraseña[/cyan] [dim](mínimo 12, recomendado 20)[/dim]",
        default=20,
    )
    if longitud < 12:
        console.print("  [yellow]⚠  Longitud mínima establecida a 12 caracteres.[/yellow]")
        longitud = 12

    usar_simbolos_str = Prompt.ask(
        "  [cyan]¿Incluir símbolos especiales?[/cyan] [dim](!@#$%...)[/dim]",
        choices=["s", "n"],
        default="s",
    )
    usar_simbolos = usar_simbolos_str.lower() == "s"

    console.print()
    with console.status("[cyan]Generando contraseña segura...[/cyan]", spinner="bouncingBall"):
        pausa(0.8)
        nueva = generar_contrasena(longitud, usar_simbolos)

    # Mostrar la contraseña generada
    console.print(
        Panel(
            Text.assemble(
                ("  🔑 Contraseña generada:\n\n", COLOR_INFO),
                (f"  {nueva}\n\n", "bold white on black"),
                ("  Cópiala y guárdala en tu gestor de contraseñas.\n", COLOR_DIM),
            ),
            border_style="cyan",
            padding=(0, 1),
        )
    )

    # Características de la contraseña
    tabla = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
    tabla.add_column("", style="cyan")
    tabla.add_column("", style="white")
    tabla.add_row("Longitud",         str(longitud))
    tabla.add_row("Mayúsculas",       "✓")
    tabla.add_row("Minúsculas",       "✓")
    tabla.add_row("Números",          "✓")
    tabla.add_row("Símbolos",         "✓" if usar_simbolos else "✗")
    tabla.add_row("Entropía aprox.", f"~{int(longitud * 6.5)} bits")
    console.print(tabla)
    console.print()

    # Ofrecer verificarla también
    verificar = Prompt.ask(
        "  [cyan]¿Quieres verificar que esta nueva contraseña no está filtrada?[/cyan]",
        choices=["s", "n"],
        default="s",
    )
    if verificar.lower() == "s":
        console.print()
        try:
            filtrada, veces = verificar_contrasena(nueva)
            if filtrada:
                # Extremadamente improbable, pero por rigor
                mostrar_resultado_filtrado(veces)
                console.print("  [yellow]Genera otra contraseña. Esta (improbablemente) ya está comprometida.[/yellow]")
            else:
                mostrar_resultado_seguro()
        except requests.RequestException as e:
            console.print(f"  [red]Error al verificar: {e}[/red]")


# ──────────────────────────────────────────────
# Menú principal
# ──────────────────────────────────────────────
def menu_post_filtrado():
    """Opciones tras detectar una contraseña filtrada."""
    tabla = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    tabla.add_column("", style="bold cyan", min_width=4)
    tabla.add_column("", style="white")
    tabla.add_row("[1]", "Generar una contraseña segura nueva")
    tabla.add_row("[2]", "Comprobar otra contraseña")
    tabla.add_row("[3]", "Salir")
    console.print(tabla)
    console.print()

    opcion = Prompt.ask("  [cyan]Elige una opción[/cyan]", choices=["1", "2", "3"], default="1")
    return opcion


def flujo_comprobar_contrasena() -> bool:
    """
    Flujo principal de comprobación.
    Devuelve True si el usuario quiere repetir, False si quiere salir.
    """
    separador("Comprobar contraseña")
    console.print()
    console.print(
        "  [dim]Tu contraseña nunca se envía. Solo se transmiten los primeros\n"
        "  5 caracteres de su hash SHA-1 (método k-Anonymity).[/dim]\n"
    )

    password = Prompt.ask("  [cyan]Introduce tu contraseña[/cyan]", password=True)

    if not password:
        console.print("  [yellow]No has introducido ninguna contraseña.[/yellow]")
        return True

    console.print()

    try:
        filtrada, veces = verificar_contrasena(password)
    except requests.ConnectionError:
        console.print(
            Panel(
                "[red]❌ Sin conexión a Internet.\n"
                "Verifica tu red e inténtalo de nuevo.[/red]",
                border_style="red",
            )
        )
        return True
    except requests.HTTPError as e:
        console.print(f"  [red]Error HTTP de la API: {e}[/red]")
        return True
    except requests.Timeout:
        console.print("  [red]⏱  La API tardó demasiado. Inténtalo de nuevo.[/red]")
        return True

    if not filtrada:
        mostrar_resultado_seguro()
        return False  # Salir tras resultado positivo

    # Contraseña filtrada
    mostrar_resultado_filtrado(veces)

    console.print("  [bold red]⚠  Recomendamos que cambies esta contraseña cuanto antes.[/bold red]\n")
    separador("¿Qué quieres hacer ahora?")
    console.print()

    opcion = menu_post_filtrado()

    if opcion == "1":
        flujo_generar_contrasena()
        return False
    elif opcion == "2":
        return True  # Volver a comprobar
    else:
        return False  # Salir


# ──────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────
def main():
    limpiar_pantalla()
    mostrar_banner()

    continuar = True
    while continuar:
        try:
            continuar = flujo_comprobar_contrasena()
            if continuar:
                console.print()
                pausa(0.5)
        except KeyboardInterrupt:
            break

    console.print()
    separador()
    console.print(
        "\n  [dim]Sesión finalizada. Recuerda usar un gestor de contraseñas. 🔐[/dim]\n"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
