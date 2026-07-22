"""Commande d'installation."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from ohanna_installer.environment import EnvironmentCheck, run_environment_checks
from ohanna_installer.github import (
    DownloadedComponent,
    DownloadError,
    download_component_packages,
    download_platform_manifest,
)
from ohanna_installer.manifest import ManifestError, PlatformManifest
from ohanna_installer.python_package import (
    InstalledPythonComponent,
    PackageInstallationError,
    create_virtual_environment,
    install_wheel,
    verify_component_command,
)
from ohanna_installer.systemd import (
    GeneratedSystemdService,
    InstalledSystemdService,
    SystemdCommandError,
    SystemdGenerationError,
    SystemdInstallationError,
    enable_systemd_services,
    generate_systemd_services,
    install_generated_services,
    reload_systemd_daemon,
)

INSTALLATION_ERROR = 3

MANIFEST_FILENAME = "release-manifest.yaml"

AGENT_IDENTIFIER = "agent"
AGENT_INSTALLATION_PATH = Path("/opt/ohanna-agent")
AGENT_ENVIRONMENT_PATH = AGENT_INSTALLATION_PATH / "venv"
AGENT_COMMAND_NAME = "ohanna-agent"
VISION_IDENTIFIER = "vision"
VISION_INSTALLATION_PATH = Path("/opt/ohanna-vision")
VISION_ENVIRONMENT_PATH = VISION_INSTALLATION_PATH / "venv"
VISION_COMMAND_NAME = "ohanna-vision"

def _reload_systemd() -> None:
    """Recharger la configuration systemd."""

    reload_systemd_daemon()

def configure_parser(subparsers: argparse._SubParsersAction) -> None:
    """Configurer la sous-commande install."""

    parser = subparsers.add_parser(
        "install",
        help="Installer les composants officiels Ohanna.",
        description="Installer les composants officiels Ohanna.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Accepter automatiquement les confirmations.",
    )
    parser.set_defaults(command_handler=run)


def _display_check(check: EnvironmentCheck) -> None:
    """Afficher le résultat d'une vérification."""

    symbol = "✓" if check.success else "✗"
    print(f"{symbol} {check.name} — {check.message}")


def _display_manifest(manifest: PlatformManifest) -> None:
    """Afficher le contenu utile du manifeste."""

    print(f"Plateforme Ohanna {manifest.platform_version}")
    print()

    for component in manifest.components:
        print(f"✓ {component.name} {component.version}")


def _load_official_manifest(directory: Path) -> PlatformManifest:
    """Télécharger et valider le manifeste officiel."""

    destination = directory / MANIFEST_FILENAME
    return download_platform_manifest(destination)


def _download_components(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[DownloadedComponent, ...]:
    """Télécharger les wheels déclarés dans le manifeste."""

    return download_component_packages(
        manifest.components,
        directory,
    )


def _find_downloaded_component(
    downloaded_components: tuple[DownloadedComponent, ...],
    identifier: str,
) -> DownloadedComponent:
    """Retrouver un composant téléchargé par son identifiant."""

    for downloaded_component in downloaded_components:
        if downloaded_component.component.identifier == identifier:
            return downloaded_component

    raise PackageInstallationError(
        f"Le composant {identifier} est absent des téléchargements."
    )


def _install_agent(
    downloaded_components: tuple[DownloadedComponent, ...],
) -> InstalledPythonComponent:
    """Installer Ohanna-Agent dans son environnement virtuel."""

    downloaded_agent = _find_downloaded_component(
        downloaded_components,
        AGENT_IDENTIFIER,
    )

    component = downloaded_agent.component

    create_virtual_environment(AGENT_ENVIRONMENT_PATH)

    install_wheel(
        downloaded_agent.path,
        AGENT_ENVIRONMENT_PATH,
    )

    return verify_component_command(
        environment_path=AGENT_ENVIRONMENT_PATH,
        command_name=AGENT_COMMAND_NAME,
        expected_version=component.version,
        component_name=component.name,
    )

def _install_vision(
    downloaded_components: tuple[DownloadedComponent, ...],
) -> InstalledPythonComponent:
    """Installer Ohanna-Vision dans son environnement virtuel."""

    downloaded_vision = _find_downloaded_component(
        downloaded_components,
        VISION_IDENTIFIER,
    )

    component = downloaded_vision.component

    create_virtual_environment(VISION_ENVIRONMENT_PATH)

    install_wheel(
        downloaded_vision.path,
        VISION_ENVIRONMENT_PATH,
    )

    return verify_component_command(
        environment_path=VISION_ENVIRONMENT_PATH,
        command_name=VISION_COMMAND_NAME,
        expected_version=component.version,
        component_name=component.name,
    )

def run(args: argparse.Namespace) -> int:
    """Exécuter la commande install."""

    del args

    print("Vérification de l'environnement...")
    print()

    checks = run_environment_checks()

    for check in checks:
        _display_check(check)

    print()

    if not all(check.success for check in checks):
        print("L'environnement ne permet pas de poursuivre l'installation.")
        return INSTALLATION_ERROR

    print("L'environnement est compatible avec Ohanna-Installer.")
    print()
    print("Téléchargement du manifeste officiel...")

    try:
        with tempfile.TemporaryDirectory(
            prefix="ohanna-installer-",
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
            print("Installation d'Ohanna-Agent...")

            installed_agent = _install_agent(downloaded_components)

            print(
                f"✓ {installed_agent.name} "
                f"{installed_agent.version} installé."
            )
            print()
            print("Installation d'Ohanna-Vision...")

            installed_vision = _install_vision(
                downloaded_components,
            )

            print(
                f"✓ {installed_vision.name} "
                f"{installed_vision.version} installé."
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
            print("Installation des services systemd...")

            installed_services = _install_services(
                generated_services,
            )

            for installed_service in installed_services:
                if installed_service.created:
                    print(
                        f"✓ {installed_service.destination_path} installé."
                    )
                else:
                    print(
                        f"✓ {installed_service.destination_path} conservé "
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

    except SystemdCommandError as error:
        print(f"✗ Commande systemd impossible : {error}")
        return INSTALLATION_ERROR
    except SystemdCommandError as error:
        print(f"✗ Rechargement systemd impossible : {error}")
        return INSTALLATION_ERROR
    except SystemdInstallationError as error:
        print(f"✗ Installation systemd impossible : {error}")
        return INSTALLATION_ERROR
    except SystemdGenerationError as error:
        print(f"✗ Génération systemd impossible : {error}")
        return INSTALLATION_ERROR
    except DownloadError as error:
        print(f"✗ Téléchargement impossible : {error}")
        return INSTALLATION_ERROR
    except ManifestError as error:
        print(f"✗ Le manifeste officiel est invalide : {error}")
        return INSTALLATION_ERROR
    except PackageInstallationError as error:
        print(f"✗ Installation impossible : {error}")
        return INSTALLATION_ERROR

    print()
    print(
        "Ohanna-Agent et Ohanna-Vision sont installés, "
        "configurés et activés au démarrage."
    )

    return 0

def _generate_services(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[GeneratedSystemdService, ...]:
    """Générer les unités systemd officielles."""

    return generate_systemd_services(
        manifest.components,
        directory / "systemd",
    )

def _install_services(
    generated_services: tuple[GeneratedSystemdService, ...],
) -> tuple[InstalledSystemdService, ...]:
    """Installer les unités systemd générées."""

    return install_generated_services(
        generated_services,
    )

def _enable_services(
    installed_services: tuple[InstalledSystemdService, ...],
) -> None:
    """Activer les services systemd installés."""

    enable_systemd_services(installed_services)