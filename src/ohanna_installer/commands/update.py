"""Commande de mise à jour."""

from __future__ import annotations

import argparse


def configure_parser(subparsers: argparse._SubParsersAction) -> None:
    """Configurer la sous-commande update."""

    parser = subparsers.add_parser(
        "update",
        help="Mettre à jour les composants officiels Ohanna.",
        description="Mettre à jour les composants officiels Ohanna.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accepter automatiquement les confirmations.",
    )
    parser.set_defaults(command_handler=run)


def run(args: argparse.Namespace) -> int:
    """Exécuter la commande update."""

    del args

    print("Mise à jour non encore implémentée.")
    return 0