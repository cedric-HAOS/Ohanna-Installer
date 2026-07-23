"""Tests d'installation des modèles de configuration."""

from pathlib import Path

import pytest

from ohanna_installer.commands.install import (
    ConfigurationInstallationError,
    _install_configuration_file,
    _install_configurations,
)
from ohanna_installer.github import DownloadedConfigurationFile
from ohanna_installer.manifest import (
    ComponentConfiguration,
    ComponentManifest,
    ComponentPackage,
    ConfigurationFile,
)


def _build_downloaded_configuration(
    tmp_path: Path,
    *,
    destination: Path = Path("plugins/dns.yaml"),
    with_component_configuration: bool = True,
) -> DownloadedConfigurationFile:
    source_path = tmp_path / "downloads" / "dns.example.yaml"
    source_path.parent.mkdir(parents=True)
    source_path.write_text("enabled: true\n", encoding="utf-8")

    configuration = ComponentConfiguration(
        directory=tmp_path / "etc" / "ohanna-agent",
        files=(
            ConfigurationFile(
                source="dns.example.yaml",
                destination=destination,
            ),
        ),
    )
    component = ComponentManifest(
        identifier="agent",
        name="Ohanna-Agent",
        repository="cedric-HAOS/Ohanna-Agent",
        version="1.1.0",
        release_tag="v1.1.0",
        package=ComponentPackage(
            type="wheel",
            filename="ohanna_agent-1.1.0-py3-none-any.whl",
        ),
        configuration=(
            configuration
            if with_component_configuration
            else None
        ),
    )

    return DownloadedConfigurationFile(
        component=component,
        configuration_file=configuration.files[0],
        path=source_path,
    )


def test_install_configuration_file_creates_nested_destination(
    tmp_path: Path,
) -> None:
    downloaded_file = _build_downloaded_configuration(tmp_path)

    installed_file = _install_configuration_file(downloaded_file)

    assert installed_file.created is True
    assert installed_file.destination_path == (
        tmp_path / "etc" / "ohanna-agent" / "plugins" / "dns.yaml"
    )
    assert installed_file.destination_path.read_text(
        encoding="utf-8"
    ) == "enabled: true\n"


def test_install_configuration_file_preserves_existing_file(
    tmp_path: Path,
) -> None:
    downloaded_file = _build_downloaded_configuration(tmp_path)
    configuration = downloaded_file.component.configuration
    assert configuration is not None

    destination = (
        configuration.directory
        / downloaded_file.configuration_file.destination
    )
    destination.parent.mkdir(parents=True)
    destination.write_text("local: true\n", encoding="utf-8")

    installed_file = _install_configuration_file(downloaded_file)

    assert installed_file.created is False
    assert destination.read_text(encoding="utf-8") == "local: true\n"


def test_install_configuration_file_rejects_directory_destination(
    tmp_path: Path,
) -> None:
    downloaded_file = _build_downloaded_configuration(
        tmp_path,
        destination=Path("dns.yaml"),
    )
    configuration = downloaded_file.component.configuration
    assert configuration is not None

    destination = (
        configuration.directory
        / downloaded_file.configuration_file.destination
    )
    destination.mkdir(parents=True)

    with pytest.raises(
        ConfigurationInstallationError,
        match="n'est pas un fichier",
    ):
        _install_configuration_file(downloaded_file)


def test_install_configuration_file_rejects_missing_source(
    tmp_path: Path,
) -> None:
    downloaded_file = _build_downloaded_configuration(tmp_path)
    downloaded_file.path.unlink()

    with pytest.raises(
        ConfigurationInstallationError,
        match="est introuvable",
    ):
        _install_configuration_file(downloaded_file)


def test_install_configuration_file_requires_component_configuration(
    tmp_path: Path,
) -> None:
    downloaded_file = _build_downloaded_configuration(
        tmp_path,
        with_component_configuration=False,
    )

    with pytest.raises(
        ConfigurationInstallationError,
        match="aucun répertoire de configuration",
    ):
        _install_configuration_file(downloaded_file)


def test_install_configurations_installs_all_files(
    tmp_path: Path,
) -> None:
    first = _build_downloaded_configuration(
        tmp_path / "first",
        destination=Path("first.yaml"),
    )
    second = _build_downloaded_configuration(
        tmp_path / "second",
        destination=Path("second.yaml"),
    )

    installed_files = _install_configurations((first, second))

    assert len(installed_files) == 2
    assert all(installed_file.created for installed_file in installed_files)
