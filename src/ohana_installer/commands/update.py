"""Commande de mise à jour."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from ohana_installer.commands.install import (
    CONFIGURATION_FILE_MODE,
    CONFIGURATION_OWNER,
    ConfigurationInstallationError,
    _check_services,
    _display_check,
    _display_manifest,
    _download_components,
    _download_configurations,
    _enable_services,
    _ensure_service_accounts,
    _generate_services,
    _install_agent,
    _install_configurations,
    _install_vision,
    _load_official_manifest,
    _reload_systemd,
    _start_services,
)
from ohana_installer.environment import run_environment_checks
from ohana_installer.github import DownloadError
from ohana_installer.manifest import ManifestError
from ohana_installer.python_package import (
    PackageInstallationError,
)
from ohana_installer.system_account import SystemAccountError
from ohana_installer.systemd import (
    GeneratedSystemdService,
    InstalledSystemdService,
    SystemdCommandError,
    SystemdGenerationError,
    SystemdInstallationError,
    install_generated_services,
    stop_systemd_service,
)

UPDATE_ERROR = 3


def configure_parser(subparsers: argparse._SubParsersAction) -> None:
    """Configurer la sous-commande update."""

    parser = subparsers.add_parser(
        "update",
        help="Mettre à jour les composants officiels Ohana.",
        description="Mettre à jour les composants officiels Ohana.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accepter automatiquement les confirmations.",
    )
    parser.set_defaults(command_handler=run)


def _stop_services(
    generated_services: tuple[GeneratedSystemdService, ...],
) -> None:
    """Arrêter les services systemd avant leur mise à jour."""

    for generated_service in generated_services:
        stop_systemd_service(generated_service.path.name)


def _replace_services(
    generated_services: tuple[GeneratedSystemdService, ...],
) -> tuple[InstalledSystemdService, ...]:
    """Installer ou remplacer les unités systemd."""

    return install_generated_services(
        generated_services,
        replace=True,
    )


def run(args: argparse.Namespace) -> int:
    """Exécuter la commande update."""

    del args

    print("Vérification de l'environnement...")
    print()

    checks = run_environment_checks()

    for check in checks:
        _display_check(check)

    print()

    if not all(check.success for check in checks):
        print("L'environnement ne permet pas de poursuivre la mise à jour.")
        return UPDATE_ERROR

    print("L'environnement est compatible avec Ohana-Installer.")
    print()
    print("Téléchargement du manifeste officiel...")

    try:
        with tempfile.TemporaryDirectory(
            prefix="ohana-installer-update-",
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)

            manifest = _load_official_manifest(temporary_path)

            print("✓ Manifeste téléchargé et validé.")
            print()

            _display_manifest(manifest)

            print()
            print("Téléchargement des composants...")

            downloaded_components = _download_components(
                manifest,
                temporary_path,
            )

            for downloaded_component in downloaded_components:
                component = downloaded_component.component
                print(
                    f"✓ {component.name} "
                    f"{component.version} téléchargé."
                )

            print()
            print("Téléchargement des configurations...")

            downloaded_configurations = _download_configurations(
                manifest,
                temporary_path,
            )

            for downloaded_configuration in downloaded_configurations:
                print(
                    "✓ "
                    f"{downloaded_configuration.configuration_file.source} "
                    "téléchargé pour "
                    f"{downloaded_configuration.component.name}."
                )

            print()
            print("Vérification des comptes système...")

            system_accounts = _ensure_service_accounts(manifest)

            for system_account in system_accounts:
                print(
                    f"✓ Groupe système {system_account.group_name} prêt."
                )
                print(
                    f"✓ Compte système {system_account.username} prêt."
                )

            print()
            print("Génération des services systemd...")

            generated_services = _generate_services(
                manifest,
                temporary_path,
            )

            for generated_service in generated_services:
                print(
                    f"✓ {generated_service.path.name} généré "
                    f"pour {generated_service.component.name}."
                )

            print()
            print("Vérification des fichiers de configuration...")

            installed_configurations = _install_configurations(
                downloaded_configurations,
            )

            for installed_configuration in installed_configurations:
                destination = installed_configuration.destination_path

                if installed_configuration.created:
                    print(
                        f"✓ {destination} installé "
                        f"({CONFIGURATION_OWNER}:"
                        f"{installed_configuration.group_name}, "
                        f"{CONFIGURATION_FILE_MODE:04o})."
                    )
                else:
                    print(
                        f"✓ {destination} conservé "
                        "(configuration locale existante, "
                        f"{CONFIGURATION_OWNER}:"
                        f"{installed_configuration.group_name}, "
                        f"{CONFIGURATION_FILE_MODE:04o})."
                    )

            print()
            print("Arrêt des services systemd...")

            _stop_services(generated_services)

            for generated_service in generated_services:
                print(f"✓ {generated_service.path.name} arrêté.")

            print()
            print("Mise à jour d'Ohana-Agent...")

            installed_agent = _install_agent(downloaded_components, replace=True)

            print(
                f"✓ {installed_agent.name} "
                f"{installed_agent.version} mis à jour."
            )

            print()
            print("Mise à jour d'Ohana-Vision...")

            installed_vision = _install_vision(
                downloaded_components,
                replace=True,
            )

            print(
                f"✓ {installed_vision.name} "
                f"{installed_vision.version} mis à jour."
            )

            print()
            print("Mise à jour des services systemd...")

            installed_services = _replace_services(
                generated_services,
            )

            for installed_service in installed_services:
                destination = installed_service.destination_path

                if installed_service.created:
                    print(f"✓ {destination} installé.")
                elif installed_service.updated:
                    print(f"✓ {destination} remplacé.")
                else:
                    print(
                        f"✓ {destination} conservé "
                        "(déjà identique)."
                    )

            print()
            print("Rechargement de systemd...")

            _reload_systemd()

            print("✓ Configuration systemd rechargée.")

            print()
            print("Activation des services systemd...")

            _enable_services(installed_services)

            for installed_service in installed_services:
                print(
                    f"✓ {installed_service.destination_path.name} activé."
                )

            print()
            print("Redémarrage des services systemd...")

            _start_services(installed_services)

            for installed_service in installed_services:
                print(
                    f"✓ {installed_service.destination_path.name} démarré."
                )

            print()
            print("Vérification des services systemd...")

            statuses = _check_services(installed_services)

            all_services_active = True

            for status in statuses:
                if status.active:
                    print(f"✓ {status.service_name} est actif.")
                else:
                    print(
                        f"✗ {status.service_name} est {status.status}."
                    )
                    all_services_active = False

            if not all_services_active:
                return UPDATE_ERROR

    except SystemdCommandError as error:
        print(f"✗ Commande systemd impossible : {error}")
        return UPDATE_ERROR
    except SystemdInstallationError as error:
        print(f"✗ Mise à jour systemd impossible : {error}")
        return UPDATE_ERROR
    except SystemdGenerationError as error:
        print(f"✗ Génération systemd impossible : {error}")
        return UPDATE_ERROR
    except DownloadError as error:
        print(f"✗ Téléchargement impossible : {error}")
        return UPDATE_ERROR
    except ManifestError as error:
        print(f"✗ Le manifeste officiel est invalide : {error}")
        return UPDATE_ERROR
    except PackageInstallationError as error:
        print(f"✗ Mise à jour impossible : {error}")
        return UPDATE_ERROR
    except ConfigurationInstallationError as error:
        print(f"✗ Mise à jour des configurations impossible : {error}")
        return UPDATE_ERROR
    except SystemAccountError as error:
        print(f"✗ Vérification des comptes système impossible : {error}")
        return UPDATE_ERROR

    print()
    print(
        "Ohana-Agent et Ohana-Vision sont mis à jour, "
        "redémarrés et vérifiés."
    )

    return 0