"""Téléchargement des artefacts officiels depuis GitHub."""

from __future__ import annotations

import urllib.error
import urllib.request
from collections.abc import Iterable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from ohana_installer.manifest import (
    ComponentManifest,
    ConfigurationFile,
    ManifestError,
    PlatformManifest,
    build_release_download_url,
    load_manifest,
)

DEFAULT_PLATFORM_REPOSITORY = "cedric-HAOS/Ohana-Platform"
DEFAULT_PLATFORM_RELEASE_TAG = "v1.0.1"
DEFAULT_MANIFEST_FILENAME = "release-manifest.yaml"
DEFAULT_TIMEOUT = 15.0


class DownloadError(RuntimeError):
    """Erreur rencontrée pendant le téléchargement d'un artefact."""


@dataclass(frozen=True)
class DownloadedComponent:
    """Composant dont le package a été téléchargé."""

    component: ComponentManifest
    path: Path


@dataclass(frozen=True)
class DownloadedConfigurationFile:
    """Fichier de configuration officiel téléchargé."""

    component: ComponentManifest
    configuration_file: ConfigurationFile
    path: Path


def build_release_asset_url(
    *,
    repository: str,
    release_tag: str,
    filename: str,
) -> str:
    """Construire l'URL GitHub d'un artefact de release."""

    return f"https://github.com/{repository}/releases/download/{release_tag}/{filename}"


def download_file(
    url: str,
    destination: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> Path:
    """Télécharger un fichier vers une destination locale."""

    destination_path = Path(destination)
    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Ohana-Installer",
            "Accept": "application/octet-stream",
        },
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:
            content = response.read()
    except urllib.error.HTTPError as error:
        raise DownloadError(
            f"Le téléchargement a échoué avec le statut HTTP {error.code} : {url}"
        ) from error
    except urllib.error.URLError as error:
        raise DownloadError(f"Le téléchargement a échoué : {error.reason}") from error
    except (TimeoutError, OSError) as error:
        raise DownloadError(f"Le téléchargement a échoué : {error}") from error

    if not content:
        raise DownloadError(f"Le fichier téléchargé depuis {url} est vide.")

    try:
        destination_path.write_bytes(content)
    except OSError as error:
        raise DownloadError(
            f"Impossible d'écrire le fichier {destination_path} : {error}"
        ) from error

    return destination_path


def download_platform_manifest(
    destination: Path | str,
    *,
    repository: str = DEFAULT_PLATFORM_REPOSITORY,
    release_tag: str = DEFAULT_PLATFORM_RELEASE_TAG,
    filename: str = DEFAULT_MANIFEST_FILENAME,
    timeout: float = DEFAULT_TIMEOUT,
) -> PlatformManifest:
    """Télécharger puis valider le manifeste officiel."""

    destination_path = Path(destination)

    url = build_release_asset_url(
        repository=repository,
        release_tag=release_tag,
        filename=filename,
    )

    downloaded_path = download_file(
        url,
        destination_path,
        timeout=timeout,
    )

    try:
        return load_manifest(downloaded_path)
    except ManifestError:
        with suppress(OSError):
            downloaded_path.unlink(missing_ok=True)

        raise


def download_component_package(
    component: ComponentManifest,
    destination_directory: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> DownloadedComponent:
    """Télécharger le package déclaré pour un composant."""

    destination_path = Path(destination_directory) / component.package.filename

    url = build_release_download_url(component)

    downloaded_path = download_file(
        url,
        destination_path,
        timeout=timeout,
    )

    return DownloadedComponent(
        component=component,
        path=downloaded_path,
    )


def download_component_packages(
    components: Iterable[ComponentManifest],
    destination_directory: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[DownloadedComponent, ...]:
    """Télécharger les packages de plusieurs composants."""

    destination_path = Path(destination_directory)
    downloaded_components: list[DownloadedComponent] = []

    for component in components:
        downloaded_components.append(
            download_component_package(
                component,
                destination_path,
                timeout=timeout,
            )
        )

    return tuple(downloaded_components)


def download_component_configuration_files(
    component: ComponentManifest,
    destination_directory: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[DownloadedConfigurationFile, ...]:
    """Télécharger les configurations officielles d'un composant."""

    if component.configuration is None:
        return ()

    component_directory = Path(destination_directory) / "configuration" / component.identifier

    downloaded_files: list[DownloadedConfigurationFile] = []

    for configuration_file in component.configuration.files:
        url = build_release_asset_url(
            repository=component.repository,
            release_tag=component.release_tag,
            filename=configuration_file.source,
        )

        destination = component_directory / configuration_file.source

        downloaded_path = download_file(
            url,
            destination,
            timeout=timeout,
        )

        downloaded_files.append(
            DownloadedConfigurationFile(
                component=component,
                configuration_file=configuration_file,
                path=downloaded_path,
            )
        )

    return tuple(downloaded_files)


def download_configuration_files(
    components: Iterable[ComponentManifest],
    destination_directory: Path | str,
    *,
    timeout: float = DEFAULT_TIMEOUT,
) -> tuple[DownloadedConfigurationFile, ...]:
    """Télécharger les configurations de tous les composants."""

    downloaded_files: list[DownloadedConfigurationFile] = []

    for component in components:
        downloaded_files.extend(
            download_component_configuration_files(
                component,
                destination_directory,
                timeout=timeout,
            )
        )

    return tuple(downloaded_files)
