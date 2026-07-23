"""Gestion des comptes système utilisés par les services Ohanna."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

DEFAULT_ACCOUNT_COMMAND_TIMEOUT = 30.0
DEFAULT_HOME_DIRECTORY = Path("/nonexistent")
DEFAULT_NOLOGIN_SHELL = Path("/usr/sbin/nologin")
ACCOUNT_NAME_PATTERN = re.compile(r"[a-z_][a-z0-9_-]*")


class SystemAccountError(RuntimeError):
    """Erreur pendant la préparation d'un compte système."""


@dataclass(frozen=True)
class SystemAccount:
    """Compte système préparé pour un service Ohanna."""

    username: str
    group_name: str
    user_created: bool
    group_created: bool


def ensure_system_account(
    username: str,
    group_name: str,
    *,
    groupadd_executable: Path | str = "groupadd",
    useradd_executable: Path | str = "useradd",
    nologin_shell: Path | str | None = None,
    timeout: float = DEFAULT_ACCOUNT_COMMAND_TIMEOUT,
) -> SystemAccount:
    """Créer ou valider un compte système et son groupe primaire."""

    _validate_account_name(username, label="utilisateur")
    _validate_account_name(group_name, label="groupe")

    group_gid = _get_group_gid(group_name)
    group_created = group_gid is None

    if group_created:
        _run_account_command(
            [
                str(groupadd_executable),
                "--system",
                group_name,
            ],
            timeout=timeout,
            description=f"création du groupe système {group_name}",
        )
        group_gid = _get_group_gid(group_name)

        if group_gid is None:
            raise SystemAccountError(
                f"Le groupe système {group_name} reste introuvable "
                "après sa création."
            )

    user_gid = _get_user_primary_gid(username)
    user_created = user_gid is None

    if user_created:
        resolved_shell = (
            Path(nologin_shell)
            if nologin_shell is not None
            else _resolve_nologin_shell()
        )

        _run_account_command(
            [
                str(useradd_executable),
                "--system",
                "--gid",
                group_name,
                "--home-dir",
                DEFAULT_HOME_DIRECTORY.as_posix(),
                "--no-create-home",
                "--shell",
                resolved_shell.as_posix(),
                username,
            ],
            timeout=timeout,
            description=f"création du compte système {username}",
        )
        user_gid = _get_user_primary_gid(username)

        if user_gid is None:
            raise SystemAccountError(
                f"Le compte système {username} reste introuvable "
                "après sa création."
            )

    if user_gid != group_gid:
        raise SystemAccountError(
            f"Le compte système {username} utilise le groupe primaire "
            f"{user_gid}, mais le groupe {group_name} utilise "
            f"l'identifiant {group_gid}."
        )

    return SystemAccount(
        username=username,
        group_name=group_name,
        user_created=user_created,
        group_created=group_created,
    )


def _validate_account_name(name: str, *, label: str) -> None:
    """Valider un nom de compte compatible avec les outils Linux."""

    if not ACCOUNT_NAME_PATTERN.fullmatch(name):
        raise SystemAccountError(
            f"Nom de {label} système invalide : {name!r}."
        )


def _get_group_gid(group_name: str) -> int | None:
    """Retourner le GID d'un groupe ou None s'il est absent."""

    try:
        import grp
    except ImportError as error:
        raise SystemAccountError(
            "La gestion des groupes système nécessite Linux."
        ) from error

    try:
        return grp.getgrnam(group_name).gr_gid
    except KeyError:
        return None


def _get_user_primary_gid(username: str) -> int | None:
    """Retourner le GID primaire d'un utilisateur ou None s'il est absent."""

    try:
        import pwd
    except ImportError as error:
        raise SystemAccountError(
            "La gestion des utilisateurs système nécessite Linux."
        ) from error

    try:
        return pwd.getpwnam(username).pw_gid
    except KeyError:
        return None


def _resolve_nologin_shell() -> Path:
    """Résoudre le shell nologin disponible sur le système."""

    executable = shutil.which("nologin")

    if executable is not None:
        return Path(executable)

    return DEFAULT_NOLOGIN_SHELL


def _run_account_command(
    command: list[str],
    *,
    timeout: float,
    description: str,
) -> None:
    """Exécuter une commande de gestion de compte système."""

    try:
        subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as error:
        raise SystemAccountError(
            f"La {description} a dépassé le délai autorisé."
        ) from error
    except subprocess.CalledProcessError as error:
        details = error.stderr.strip() or error.stdout.strip()

        if details:
            raise SystemAccountError(
                f"La {description} a échoué : {details}"
            ) from error

        raise SystemAccountError(
            f"La {description} a échoué."
        ) from error
    except OSError as error:
        raise SystemAccountError(
            f"Impossible d'exécuter la {description} : {error}"
        ) from error
