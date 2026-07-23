"""Tests de la commande de mise à jour."""

from __future__ import annotations

from pathlib import Path

import pytest

from ohanna_installer.cli import main
from ohanna_installer.environment import EnvironmentCheck
from ohanna_installer.github import DownloadedComponent
from ohanna_installer.manifest import (
    CompatibilityManifest,
    ComponentManifest,
    ComponentPackage,
    PlatformManifest,
    RuntimeManifest,
)
from ohanna_installer.python_package import InstalledPythonComponent
from ohanna_installer.system_account import SystemAccount
from ohanna_installer.systemd import (
    GeneratedSystemdService,
    InstalledSystemdService,
    SystemdCommandError,
    SystemdServiceStatus,
)


def _build_manifest() -> PlatformManifest:
    return PlatformManifest(
        schema_version=1,
        platform_name="Ohanna",
        platform_version="1.1.0",
        runtime=RuntimeManifest(
            minimum_python_version="3.12",
        ),
        components=(
            ComponentManifest(
                identifier="agent",
                name="Ohanna-Agent",
                repository="cedric-HAOS/Ohanna-Agent",
                version="1.1.0",
                release_tag="v1.1.0",
                package=ComponentPackage(
                    type="wheel",
                    filename="ohanna_agent-1.1.0-py3-none-any.whl",
                ),
            ),
            ComponentManifest(
                identifier="vision",
                name="Ohanna-Vision",
                repository="cedric-HAOS/Ohanna-Vision",
                version="1.1.0",
                release_tag="v1.1.0",
                package=ComponentPackage(
                    type="wheel",
                    filename="ohanna_vision-1.1.0-py3-none-any.whl",
                ),
            ),
        ),
        compatibility=CompatibilityManifest(
            operating_system_family="Linux",
            service_manager="systemd",
        ),
    )


def _build_downloaded_components(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[DownloadedComponent, ...]:
    return tuple(
        DownloadedComponent(
            component=component,
            path=directory / component.package.filename,
        )
        for component in manifest.components
    )


def _build_generated_services(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[GeneratedSystemdService, ...]:
    return tuple(
        GeneratedSystemdService(
            component=component,
            path=directory / f"ohanna-{component.identifier}.service",
            content="[Unit]\n",
        )
        for component in manifest.components
    )


def _build_installed_services(
    manifest: PlatformManifest,
) -> tuple[InstalledSystemdService, ...]:
    return tuple(
        InstalledSystemdService(
            component=component,
            source_path=Path(
                f"/tmp/ohanna-{component.identifier}.service"
            ),
            destination_path=Path(
                f"/etc/systemd/system/"
                f"ohanna-{component.identifier}.service"
            ),
            created=False,
            updated=True,
        )
        for component in manifest.components
    )


def _build_installed_component(
    name: str,
    command_name: str,
) -> InstalledPythonComponent:
    identifier = command_name.removeprefix("ohanna-")

    return InstalledPythonComponent(
        name=name,
        version="1.1.0",
        environment_path=Path(f"/opt/ohanna-{identifier}/venv"),
        executable_path=Path(
            f"/opt/ohanna-{identifier}/venv/bin/{command_name}"
        ),
    )


def test_update_updates_and_restarts_official_components(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()
    generated_services = _build_generated_services(
        manifest,
        Path("/tmp/systemd"),
    )
    installed_services = _build_installed_services(manifest)

    operations: list[str] = []

    monkeypatch.setattr(
        "ohanna_installer.commands.update.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._download_configurations",
        lambda manifest, directory: (
            operations.append("download-config") or ()
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._ensure_service_accounts",
        lambda manifest: (
            operations.append("account")
            or (
                SystemAccount(
                    username="ohanna",
                    group_name="ohanna",
                    user_created=False,
                    group_created=False,
                ),
            )
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._generate_services",
        lambda manifest, directory: generated_services,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._install_configurations",
        lambda downloaded_files: (
            operations.append("config") or ()
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._stop_services",
        lambda services: operations.append("stop"),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._install_agent",
        lambda components: (
            operations.append("agent")
            or _build_installed_component(
                "Ohanna-Agent",
                "ohanna-agent",
            )
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._install_vision",
        lambda components: (
            operations.append("vision")
            or _build_installed_component(
                "Ohanna-Vision",
                "ohanna-vision",
            )
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._replace_services",
        lambda services: (
            operations.append("replace")
            or installed_services
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._reload_systemd",
        lambda: operations.append("reload"),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._enable_services",
        lambda services: operations.append("enable"),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._start_services",
        lambda services: operations.append("start"),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._check_services",
        lambda services: (
            operations.append("check")
            or (
                SystemdServiceStatus(
                    service_name="ohanna-agent.service",
                    active=True,
                    status="active",
                ),
                SystemdServiceStatus(
                    service_name="ohanna-vision.service",
                    active=True,
                    status="active",
                ),
            )
        ),
    )

    assert main(["update"]) == 0

    assert operations == [
        "download-config",
        "account",
        "config",
        "stop",
        "agent",
        "vision",
        "replace",
        "reload",
        "enable",
        "start",
        "check",
    ]

    output = capsys.readouterr().out

    assert "Téléchargement des configurations" in output
    assert "Vérification des comptes système" in output
    assert "Compte système ohanna prêt" in output
    assert "Vérification des fichiers de configuration" in output
    assert "Arrêt des services systemd" in output
    assert "Ohanna-Agent 1.1.0 mis à jour" in output
    assert "Ohanna-Vision 1.1.0 mis à jour" in output
    assert "ohanna-agent.service est actif" in output
    assert "ohanna-vision.service est actif" in output
    assert (
        "Ohanna-Agent et Ohanna-Vision sont mis à jour, "
        "redémarrés et vérifiés."
    ) in output


def test_update_fails_when_environment_is_incompatible(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_called = False

    def load_manifest(directory: Path) -> PlatformManifest:
        del directory

        nonlocal manifest_called
        manifest_called = True

        return _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.update.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=False,
                message="Non compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._load_official_manifest",
        load_manifest,
    )

    assert main(["update"]) == 3
    assert manifest_called is False

    output = capsys.readouterr().out
    assert "ne permet pas de poursuivre la mise à jour" in output


def test_update_fails_when_service_stop_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()
    generated_services = _build_generated_services(
        manifest,
        Path("/tmp/systemd"),
    )

    monkeypatch.setattr(
        "ohanna_installer.commands.update.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._generate_services",
        lambda manifest, directory: generated_services,
    )

    def raise_stop_error(
        services: tuple[GeneratedSystemdService, ...],
    ) -> None:
        del services
        raise SystemdCommandError("arrêt refusé")

    monkeypatch.setattr(
        "ohanna_installer.commands.update._stop_services",
        raise_stop_error,
    )

    assert main(["update"]) == 3

    output = capsys.readouterr().out
    assert "Commande systemd impossible" in output
    assert "arrêt refusé" in output


def test_update_fails_when_service_remains_inactive(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()
    generated_services = _build_generated_services(
        manifest,
        Path("/tmp/systemd"),
    )
    installed_services = _build_installed_services(manifest)

    monkeypatch.setattr(
        "ohanna_installer.commands.update.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._generate_services",
        lambda manifest, directory: generated_services,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._stop_services",
        lambda services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._install_agent",
        lambda components: _build_installed_component(
            "Ohanna-Agent",
            "ohanna-agent",
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._install_vision",
        lambda components: _build_installed_component(
            "Ohanna-Vision",
            "ohanna-vision",
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._replace_services",
        lambda services: installed_services,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._enable_services",
        lambda services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._start_services",
        lambda services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.update._check_services",
        lambda services: (
            SystemdServiceStatus(
                service_name="ohanna-agent.service",
                active=False,
                status="failed",
            ),
            SystemdServiceStatus(
                service_name="ohanna-vision.service",
                active=True,
                status="active",
            ),
        ),
    )

    assert main(["update"]) == 3

    output = capsys.readouterr().out
    assert "ohanna-agent.service est failed" in output
    assert "ohanna-vision.service est actif" in output