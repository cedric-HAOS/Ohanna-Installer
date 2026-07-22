"""Interface en ligne de commande d'Ohanna-Installer."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from ohanna_installer.commands import install, uninstall, update
from ohanna_installer.version import __version__


def build_parser() -> argparse.ArgumentParser:
    """Construire le parseur principal de la CLI."""

    parser = argparse.ArgumentParser(
        prog="ohanna",
        description=(
            "Installer, mettre à jour et désinstaller les composants "
            "officiels de l'écosystème Ohanna."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        title="commandes",
        metavar="{install,update,uninstall}",
        required=True,
    )

    install.configure_parser(subparsers)
    update.configure_parser(subparsers)
    uninstall.configure_parser(subparsers)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Exécuter l'interface en ligne de commande."""

    parser = build_parser()
    args = parser.parse_args(argv)

    command_handler = args.command_handler
    return command_handler(args)