"""Commande d'installation."""

from __future__ import annotations

import argparse
import shutil
import tempfile
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from ohana_installer.administration import (
    AdministrationPreparationError,
    activate_administration,
    prepare_administration,
)
from ohana_installer.confirmation import confirm_action
from ohana_installer.environment import EnvironmentCheck, run_environment_checks
from ohana_installer.github import (
    DownloadedComponent,
    DownloadedConfigurationFile,
    DownloadError,
    download_component_packages,
    download_configuration_files,
    download_platform_manifest,
)
from ohana_installer.manifest import (
    ComponentManifest,
    ManifestError,
    PlatformManifest,
)
from ohana_installer.python_package import (
    InstalledPythonComponent,
    PackageInstallationError,
    create_virtual_environment,
    install_wheel,
    secure_installation_tree,
    verify_component_command,
)
from ohana_installer.system_account import (
    SystemAccount,
    SystemAccountError,
    ensure_system_account,
)
from ohana_installer.systemd import (
    GeneratedSystemdService,
    InstalledSystemdService,
    SystemdCommandError,
    SystemdGenerationError,
    SystemdInstallationError,
    SystemdServiceStatus,
    enable_systemd_services,
    generate_systemd_services,
    get_systemd_services_status,
    install_generated_services,
    reload_systemd_daemon,
    start_systemd_services,
)

INSTALLATION_ERROR = 3

MANIFEST_FILENAME = "release-manifest.yaml"

AGENT_IDENTIFIER = "agent"
AGENT_INSTALLATION_PATH = Path("/opt/ohana-agent")
AGENT_ENVIRONMENT_PATH = AGENT_INSTALLATION_PATH / "venv"
AGENT_COMMAND_NAME = "ohana-agent"
VISION_IDENTIFIER = "vision"
VISION_INSTALLATION_PATH = Path("/opt/ohana-vision")
VISION_ENVIRONMENT_PATH = VISION_INSTALLATION_PATH / "venv"
VISION_COMMAND_NAME = "ohana-vision"

INSTALLATION_OWNER = "root"
CONFIGURATION_OWNER = "root"
CONFIGURATION_DIRECTORY_MODE = 0o750
CONFIGURATION_FILE_MODE = 0o640


class ConfigurationInstallationError(RuntimeError):
    """Erreur rencontrée pendant l'installation d'une configuration."""


@dataclass(frozen=True)
class InstalledConfigurationFile:
    """Fichier de configuration installé ou conservé."""

    component_name: str
    source_path: Path
    destination_path: Path
    group_name: str
    created: bool


def _reload_systemd() -> None:
    """Recharger la configuration systemd."""

    reload_systemd_daemon()


def configure_parser(subparsers: argparse._SubParsersAction) -> None:
    """Configurer la sous-commande install."""

    parser = subparsers.add_parser(
        "install",
        help="Installer les composants officiels Ohana.",
        description="Installer les composants officiels Ohana.",
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

    print(f"Plateforme Ohana {manifest.platform_version}")
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


def _download_configurations(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[DownloadedConfigurationFile, ...]:
    """Télécharger les modèles de configuration déclarés."""

    return download_configuration_files(
        manifest.components,
        directory,
    )


def _configuration_group_name(component: ComponentManifest) -> str:
    """Retourner le groupe autorisé à lire la configuration."""

    if component.service is None:
        return CONFIGURATION_OWNER

    return component.service.group


def _configuration_directories(
    configuration_directory: Path,
    destination_path: Path,
) -> tuple[Path, ...]:
    """Lister les répertoires déclarés jusqu'au fichier final."""

    try:
        relative_parent = destination_path.parent.relative_to(configuration_directory)
    except ValueError as error:
        raise ConfigurationInstallationError(
            f"La destination {destination_path} sort du répertoire "
            f"de configuration {configuration_directory}."
        ) from error

    directories = [configuration_directory]
    current_directory = configuration_directory

    for part in relative_parent.parts:
        current_directory /= part
        directories.append(current_directory)

    return tuple(directories)


def _secure_configuration_path(
    path: Path,
    *,
    group_name: str,
    mode: int,
) -> None:
    """Appliquer un propriétaire, un groupe et un mode explicites."""

    try:
        shutil.chown(
            path,
            user=CONFIGURATION_OWNER,
            group=group_name,
        )
        path.chmod(mode)
    except (LookupError, OSError) as error:
        raise ConfigurationInstallationError(
            f"Impossible de sécuriser {path} "
            f"({CONFIGURATION_OWNER}:{group_name}, {mode:04o}) : "
            f"{error}"
        ) from error


def _prepare_configuration_directories(
    configuration_directory: Path,
    destination_path: Path,
    *,
    group_name: str,
) -> None:
    """Créer et sécuriser l'arborescence d'une configuration."""

    for directory in _configuration_directories(
        configuration_directory,
        destination_path,
    ):
        try:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as error:
            raise ConfigurationInstallationError(
                f"Impossible de préparer {directory} : {error}"
            ) from error

        if directory.is_symlink():
            raise ConfigurationInstallationError(
                f"Le répertoire de configuration {directory} ne peut pas être un lien symbolique."
            )

        if not directory.is_dir():
            raise ConfigurationInstallationError(
                f"Le chemin de configuration {directory} n'est pas un répertoire."
            )

        _secure_configuration_path(
            directory,
            group_name=group_name,
            mode=CONFIGURATION_DIRECTORY_MODE,
        )


def _install_configuration_file(
    downloaded_file: DownloadedConfigurationFile,
) -> InstalledConfigurationFile:
    """Installer un modèle et imposer des permissions sécurisées."""

    component = downloaded_file.component
    configuration = component.configuration

    if configuration is None:
        raise ConfigurationInstallationError(
            f"{component.name} ne déclare aucun répertoire de configuration."
        )

    source_path = downloaded_file.path
    destination_path = configuration.directory / downloaded_file.configuration_file.destination
    group_name = _configuration_group_name(component)

    if not source_path.is_file():
        raise ConfigurationInstallationError(
            f"Le modèle de configuration {source_path} est introuvable."
        )

    if destination_path.is_symlink():
        raise ConfigurationInstallationError(
            f"La destination {destination_path} ne peut pas être un lien symbolique."
        )

    if destination_path.exists() and not destination_path.is_file():
        raise ConfigurationInstallationError(
            f"La destination {destination_path} existe mais n'est pas un fichier."
        )

    _prepare_configuration_directories(
        configuration.directory,
        destination_path,
        group_name=group_name,
    )

    created = not destination_path.exists()

    if created:
        try:
            shutil.copy2(
                source_path,
                destination_path,
            )
        except OSError as error:
            raise ConfigurationInstallationError(
                f"Impossible d'installer {destination_path} : {error}"
            ) from error

    try:
        _secure_configuration_path(
            destination_path,
            group_name=group_name,
            mode=CONFIGURATION_FILE_MODE,
        )
    except ConfigurationInstallationError:
        if created:
            with suppress(OSError):
                destination_path.unlink(missing_ok=True)

        raise

    return InstalledConfigurationFile(
        component_name=component.name,
        source_path=source_path,
        destination_path=destination_path,
        group_name=group_name,
        created=created,
    )


def _install_configurations(
    downloaded_files: tuple[DownloadedConfigurationFile, ...],
) -> tuple[InstalledConfigurationFile, ...]:
    """Installer tous les modèles de configuration téléchargés."""

    return tuple(
        _install_configuration_file(downloaded_file) for downloaded_file in downloaded_files
    )


def _ensure_service_accounts(
    manifest: PlatformManifest,
) -> tuple[SystemAccount, ...]:
    """Créer ou valider les comptes déclarés par les services."""

    account_names = {
        (component.service.user, component.service.group)
        for component in manifest.components
        if component.service is not None
    }

    return tuple(
        ensure_system_account(username, group_name)
        for username, group_name in sorted(account_names)
    )


def _find_downloaded_component(
    downloaded_components: tuple[DownloadedComponent, ...],
    identifier: str,
) -> DownloadedComponent:
    """Retrouver un composant téléchargé par son identifiant."""

    for downloaded_component in downloaded_components:
        if downloaded_component.component.identifier == identifier:
            return downloaded_component

    raise PackageInstallationError(f"Le composant {identifier} est absent des téléchargements.")


def _prepare_installation_path(
    installation_path: Path,
    *,
    replace: bool,
) -> bool:
    """Validate an installation path and optionally remove it."""

    if installation_path.is_symlink():
        raise PackageInstallationError(
            f"Le répertoire d'installation {installation_path} ne peut pas être un lien symbolique."
        )

    if installation_path.exists() and not installation_path.is_dir():
        raise PackageInstallationError(
            f"Le chemin d'installation {installation_path} n'est pas un répertoire."
        )

    if not replace or not installation_path.exists():
        return False

    try:
        shutil.rmtree(installation_path)
    except OSError as error:
        raise PackageInstallationError(
            f"Impossible de remplacer l'installation {installation_path} : {error}"
        ) from error

    return True


def _installation_group_name(component: ComponentManifest) -> str:
    """Return the group allowed to execute one component."""

    if component.service is None:
        return INSTALLATION_OWNER

    return component.service.group


def _install_component(
    downloaded_components: tuple[DownloadedComponent, ...],
    *,
    identifier: str,
    installation_path: Path,
    environment_path: Path,
    command_name: str,
    replace: bool,
) -> InstalledPythonComponent:
    """Install and secure one Python component."""

    downloaded_component = _find_downloaded_component(
        downloaded_components,
        identifier,
    )
    component = downloaded_component.component
    installation_existed = installation_path.exists()

    _prepare_installation_path(
        installation_path,
        replace=replace,
    )

    cleanup_on_failure = replace or not installation_existed

    try:
        create_virtual_environment(environment_path)
        install_wheel(
            downloaded_component.path,
            environment_path,
        )
        installed_component = verify_component_command(
            environment_path=environment_path,
            command_name=command_name,
            expected_version=component.version,
            component_name=component.name,
        )
        secure_installation_tree(
            installation_path,
            owner=INSTALLATION_OWNER,
            group=_installation_group_name(component),
        )
    except PackageInstallationError:
        if cleanup_on_failure:
            with suppress(OSError):
                shutil.rmtree(installation_path)

        raise

    return installed_component


def _install_agent(
    downloaded_components: tuple[DownloadedComponent, ...],
    *,
    replace: bool = False,
) -> InstalledPythonComponent:
    """Install Ohana-Agent in its virtual environment."""

    return _install_component(
        downloaded_components,
        identifier=AGENT_IDENTIFIER,
        installation_path=AGENT_INSTALLATION_PATH,
        environment_path=AGENT_ENVIRONMENT_PATH,
        command_name=AGENT_COMMAND_NAME,
        replace=replace,
    )


def _install_vision(
    downloaded_components: tuple[DownloadedComponent, ...],
    *,
    replace: bool = False,
) -> InstalledPythonComponent:
    """Install Ohana-Vision in its virtual environment."""

    return _install_component(
        downloaded_components,
        identifier=VISION_IDENTIFIER,
        installation_path=VISION_INSTALLATION_PATH,
        environment_path=VISION_ENVIRONMENT_PATH,
        command_name=VISION_COMMAND_NAME,
        replace=replace,
    )


def run(args: argparse.Namespace) -> int:
    """Exécuter la commande install."""

    assume_yes = bool(args.yes)

    print("Vérification de l'environnement...")
    print()

    checks = run_environment_checks()

    for check in checks:
        _display_check(check)

    print()

    if not all(check.success for check in checks):
        print("L'environnement ne permet pas de poursuivre l'installation.")
        return INSTALLATION_ERROR

    print("L'environnement est compatible avec Ohana-Installer.")
    print()
    print("Téléchargement du manifeste officiel...")

    try:
        with tempfile.TemporaryDirectory(
            prefix="ohana-installer-",
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)

            manifest = _load_official_manifest(temporary_path)

            print("✓ Manifeste téléchargé et validé.")
            print()

            _display_manifest(manifest)

            print()

            if not confirm_action(
                "Installer cette release de la plateforme Ohana ?",
                assume_yes=assume_yes,
            ):
                print("Installation annulée.")
                return 0

            print()
            print("Téléchargement des composants...")

            downloaded_components = _download_components(
                manifest,
                temporary_path,
            )

            for downloaded_component in downloaded_components:
                component = downloaded_component.component
                print(f"✓ {component.name} {component.version} téléchargé.")

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
            print("Préparation des comptes système...")

            system_accounts = _ensure_service_accounts(manifest)

            for system_account in system_accounts:
                group_status = "créé" if system_account.group_created else "déjà présent"
                user_status = "créé" if system_account.user_created else "déjà présent"

                print(f"✓ Groupe système {system_account.group_name} {group_status}.")
                print(f"✓ Compte système {system_account.username} {user_status}.")

            print()
            print("Installation d'Ohana-Agent...")

            installed_agent = _install_agent(downloaded_components)

            print(f"✓ {installed_agent.name} {installed_agent.version} installé.")
            print()
            print("Installation d'Ohana-Vision...")

            installed_vision = _install_vision(
                downloaded_components,
            )

            print(f"✓ {installed_vision.name} {installed_vision.version} installé.")
            print()
            print("Installation des fichiers de configuration...")

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
            print("Préparation de l'administration graphique...")

            administration = prepare_administration()

            if administration.configured:
                print("✓ Canal Agent/Vision sécurisé et configuré.")

                if administration.dhcp_enabled:
                    print("✓ Administration DHCP dnsmasq préparée.")
                else:
                    print("✓ DHCP absent : administration DHCP désactivée.")

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
                    print(f"✓ {installed_service.destination_path} installé.")
                else:
                    print(f"✓ {installed_service.destination_path} conservé (déjà identique).")
            print()
            print("Rechargement de systemd...")

            _reload_systemd()

            print("✓ Configuration systemd rechargée.")
            activate_administration(administration)

            if administration.dhcp_enabled:
                print("✓ Surveillance du rechargement DHCP activée.")

            print()
            print("Activation des services systemd...")

            _enable_services(installed_services)

            for installed_service in installed_services:
                print(f"✓ {installed_service.destination_path.name} activé.")
            print()
            print("Démarrage des services systemd...")

            _start_services(installed_services)

            for installed_service in installed_services:
                print(f"✓ {installed_service.destination_path.name} démarré.")
            print()
            print("Vérification des services systemd...")

            statuses = _check_services(installed_services)

            for status in statuses:
                if status.active:
                    print(f"✓ {status.service_name} est actif.")
                else:
                    print(f"✗ {status.service_name} est {status.status}.")
                    return INSTALLATION_ERROR

    except SystemdCommandError as error:
        print(f"✗ Commande systemd impossible : {error}")
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
    except ConfigurationInstallationError as error:
        print(f"✗ Installation des configurations impossible : {error}")
        return INSTALLATION_ERROR
    except AdministrationPreparationError as error:
        print(f"✗ Préparation de l'administration impossible : {error}")
        return INSTALLATION_ERROR
    except SystemAccountError as error:
        print(f"✗ Préparation des comptes système impossible : {error}")
        return INSTALLATION_ERROR

    print()
    print("Ohana-Agent et Ohana-Vision sont installés, configurés, activés et démarrés.")

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


def _start_services(
    installed_services: tuple[InstalledSystemdService, ...],
) -> None:
    """Démarrer les services systemd installés."""

    start_systemd_services(installed_services)


def _check_services(
    installed_services: tuple[InstalledSystemdService, ...],
) -> tuple[SystemdServiceStatus, ...]:
    """Vérifier l'état des services systemd."""

    return get_systemd_services_status(installed_services)
