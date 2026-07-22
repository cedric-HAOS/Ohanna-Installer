"""Commande de désinstallation."""

from __future__ import annotations

import argparse


def configure_parser(subparsers: argparse._SubParsersAction) -> None:
    """Configurer la sous-commande uninstall."""

    parser = subparsers.add_parser(
        "uninstall",
        help="Désinstaller les composants officiels Ohanna.",
        description="Désinstaller les composants officiels Ohanna.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accepter automatiquement les confirmations.",
    )
    parser.set_defaults(command_handler=run)


def run(args: argparse.Namespace) -> int:
    """Exécuter la commande uninstall."""

    del args

    print("Désinstallation non encore implémentée.")
    return 0