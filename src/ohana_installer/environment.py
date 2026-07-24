"""Vérification de l'environnement d'installation."""

from __future__ import annotations

import os
import platform
import shutil
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

MINIMUM_PYTHON_VERSION = (3, 13)
GITHUB_URL = "https://github.com"


@dataclass(frozen=True)
class EnvironmentCheck:
    """Résultat d'une vérification de l'environnement."""

    name: str
    success: bool
    message: str


def check_linux() -> EnvironmentCheck:
    """Vérifier que le système d'exploitation est Linux."""

    system_name = platform.system()

    if system_name == "Linux":
        return EnvironmentCheck(
            name="Système d'exploitation",
            success=True,
            message="Linux détecté.",
        )

    return EnvironmentCheck(
        name="Système d'exploitation",
        success=False,
        message=f"Système non pris en charge : {system_name}.",
    )


def check_systemd() -> EnvironmentCheck:
    """Vérifier que systemd est disponible."""

    systemctl_path = shutil.which("systemctl")

    if systemctl_path is not None:
        return EnvironmentCheck(
            name="systemd",
            success=True,
            message=f"systemctl détecté : {systemctl_path}.",
        )

    return EnvironmentCheck(
        name="systemd",
        success=False,
        message="La commande systemctl est introuvable.",
    )


def check_python_version() -> EnvironmentCheck:
    """Vérifier que la version de Python est compatible."""

    current_version = sys.version_info[:3]
    formatted_version = ".".join(str(part) for part in current_version)

    if current_version >= MINIMUM_PYTHON_VERSION:
        return EnvironmentCheck(
            name="Python",
            success=True,
            message=f"Python {formatted_version} compatible.",
        )

    minimum_version = ".".join(str(part) for part in MINIMUM_PYTHON_VERSION)

    return EnvironmentCheck(
        name="Python",
        success=False,
        message=(
            f"Python {formatted_version} détecté ; "
            f"Python {minimum_version} ou supérieur est requis."
        ),
    )


def check_pip() -> EnvironmentCheck:
    """Vérifier que pip est disponible."""

    try:
        import pip  # noqa: F401
    except ImportError:
        return EnvironmentCheck(
            name="pip",
            success=False,
            message="pip est indisponible dans l'environnement Python courant.",
        )

    return EnvironmentCheck(
        name="pip",
        success=True,
        message="pip est disponible.",
    )


def check_administrator() -> EnvironmentCheck:
    """Vérifier que l'installateur dispose des droits administrateur."""

    if not hasattr(os, "geteuid"):
        return EnvironmentCheck(
            name="Privilèges",
            success=False,
            message="La vérification des privilèges nécessite Linux.",
        )

    if os.geteuid() == 0:
        return EnvironmentCheck(
            name="Privilèges",
            success=True,
            message="Exécution avec les privilèges administrateur.",
        )

    return EnvironmentCheck(
        name="Privilèges",
        success=False,
        message="La commande doit être exécutée avec sudo.",
    )


def check_github_connectivity(
    *,
    url: str = GITHUB_URL,
    timeout: float = 5.0,
) -> EnvironmentCheck:
    """Vérifier que GitHub est accessible."""

    request = urllib.request.Request(
        url,
        method="HEAD",
        headers={"User-Agent": "Ohana-Installer"},
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = response.status
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return EnvironmentCheck(
            name="Accès GitHub",
            success=False,
            message=f"GitHub est inaccessible : {error}.",
        )

    if 200 <= status < 400:
        return EnvironmentCheck(
            name="Accès GitHub",
            success=True,
            message="GitHub est accessible.",
        )

    return EnvironmentCheck(
        name="Accès GitHub",
        success=False,
        message=f"GitHub a répondu avec le statut HTTP {status}.",
    )


def run_environment_checks() -> tuple[EnvironmentCheck, ...]:
    """Exécuter toutes les vérifications de l'environnement."""

    return (
        check_linux(),
        check_systemd(),
        check_python_version(),
        check_pip(),
        check_administrator(),
        check_github_connectivity(),
    )
