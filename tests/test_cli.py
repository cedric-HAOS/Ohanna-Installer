"""Tests de l'interface en ligne de commande."""

from __future__ import annotations

from pathlib import Path

import pytest

from ohanna_installer.cli import main
from ohanna_installer.environment import EnvironmentCheck
from ohanna_installer.github import DownloadedComponent, DownloadError
from ohanna_installer.manifest import (
    CompatibilityManifest,
    ComponentManifest,
    ComponentPackage,
    ManifestError,
    PlatformManifest,
    RuntimeManifest,
)
from ohanna_installer.python_package import (
    InstalledPythonComponent,
    PackageInstallationError,
)
from ohanna_installer.system_account import SystemAccount
from ohanna_installer.systemd import (
    GeneratedSystemdService,
    InstalledSystemdService,
    SystemdCommandError,
    SystemdInstallationError,
    SystemdServiceStatus,
)
from ohanna_installer.version import __version__


def _build_manifest() -> PlatformManifest:
    return PlatformManifest(
        schema_version=1,
        platform_name="Ohanna",
        platform_version="1.0.0",
        runtime=RuntimeManifest(
            minimum_python_version="3.12",
        ),
        components=(
            ComponentManifest(
                identifier="agent",
                name="Ohanna-Agent",
                repository="cedric-HAOS/Ohanna-Agent",
                version="1.0.0",
                release_tag="v1.0.0",
                package=ComponentPackage(
                    type="wheel",
                    filename="ohanna_agent-1.0.0-py3-none-any.whl",
                ),
            ),
            ComponentManifest(
                identifier="vision",
                name="Ohanna-Vision",
                repository="cedric-HAOS/Ohanna-Vision",
                version="1.0.0",
                release_tag="v1.0.0",
                package=ComponentPackage(
                    type="wheel",
                    filename="ohanna_vision-1.0.0-py3-none-any.whl",
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


def _build_installed_agent() -> InstalledPythonComponent:
    return InstalledPythonComponent(
        name="Ohanna-Agent",
        version="1.0.0",
        environment_path=Path("/opt/ohanna-agent/venv"),
        executable_path=Path(
            "/opt/ohanna-agent/venv/bin/ohanna-agent"
        ),
    )


def _build_installed_services(
    manifest: PlatformManifest,
    directory: Path,
) -> tuple[InstalledSystemdService, ...]:
    agent = next(
        component
        for component in manifest.components
        if component.identifier == "agent"
    )
    vision = next(
        component
        for component in manifest.components
        if component.identifier == "vision"
    )

    return (
        InstalledSystemdService(
            component=agent,
            source_path=directory / "ohanna-agent.service",
            destination_path=Path(
                "/etc/systemd/system/ohanna-agent.service"
            ),
            created=True,
        ),
        InstalledSystemdService(
            component=vision,
            source_path=directory / "ohanna-vision.service",
            destination_path=Path(
                "/etc/systemd/system/ohanna-vision.service"
            ),
            created=True,
        ),
    )


def test_cli_requires_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([])

    assert exc_info.value.code == 2

    error_output = capsys.readouterr().err
    assert "the following arguments are required" in error_output


def test_cli_displays_version(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    assert capsys.readouterr().out.strip() == f"ohanna {__version__}"


def test_cli_displays_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(["--help"])

    assert exc_info.value.code == 0

    output = capsys.readouterr().out

    assert "usage: ohanna" in output
    assert "install" in output
    assert "update" in output
    assert "uninstall" in output
    assert "--version" in output

@pytest.mark.parametrize(
    "command",
    [
        "install",
        "update",
        "uninstall",
    ],
)
def test_command_displays_help(
    command: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main([command, "--help"])

    assert exc_info.value.code == 0

    output = capsys.readouterr().out

    assert f"usage: ohanna {command}" in output
    assert "--yes" in output


def test_install_fails_when_environment_is_incompatible(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest_loader_called = False

    def load_manifest(directory: Path) -> PlatformManifest:
        del directory

        nonlocal manifest_loader_called
        manifest_loader_called = True

        return _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=False,
                message="Non compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        load_manifest,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "✗ Linux" in output
    assert "ne permet pas de poursuivre" in output
    assert manifest_loader_called is False


def test_install_fails_when_manifest_download_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )

    def raise_download_error(
        directory: Path,
    ) -> PlatformManifest:
        del directory
        raise DownloadError("connexion refusée")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        raise_download_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Téléchargement impossible" in output
    assert "connexion refusée" in output


def test_install_fails_when_manifest_is_invalid(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )

    def raise_manifest_error(
        directory: Path,
    ) -> PlatformManifest:
        del directory
        raise ManifestError("schéma invalide")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        raise_manifest_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "manifeste officiel est invalide" in output
    assert "schéma invalide" in output


def test_load_official_manifest_uses_expected_destination(
    tmp_path: Path,
    monkeypatch,
) -> None:
    expected_manifest = _build_manifest()
    received_destination: Path | None = None

    def fake_download(
        destination: Path,
    ) -> PlatformManifest:
        nonlocal received_destination
        received_destination = destination

        return expected_manifest

    monkeypatch.setattr(
        "ohanna_installer.commands.install.download_platform_manifest",
        fake_download,
    )

    from ohanna_installer.commands.install import (
        _load_official_manifest,
    )

    result = _load_official_manifest(tmp_path)

    assert result == expected_manifest
    assert received_destination == (
        tmp_path / "release-manifest.yaml"
    )


def test_install_downloads_and_installs_official_components(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._ensure_service_accounts",
        lambda manifest: (
            SystemAccount(
                username="ohanna",
                group_name="ohanna",
                user_created=True,
                group_created=True,
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: _build_installed_services(
            manifest,
            Path("/tmp/systemd"),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._enable_services",
        lambda installed_services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._check_services",
        lambda installed_services: (
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
        ),
    )

    assert main(["install"]) == 0

    output = capsys.readouterr().out

    assert "Téléchargement des composants" in output
    assert "✓ Ohanna-Agent 1.0.0 téléchargé." in output
    assert "✓ Ohanna-Vision 1.0.0 téléchargé." in output
    assert "Téléchargement des configurations" in output
    assert "Préparation des comptes système" in output
    assert "Groupe système ohanna créé" in output
    assert "Compte système ohanna créé" in output
    assert "Installation d'Ohanna-Agent" in output
    assert "✓ Ohanna-Agent 1.0.0 installé." in output
    assert "Installation d'Ohanna-Vision" in output
    assert "✓ Ohanna-Vision 1.0.0 installé." in output
    assert "Installation des fichiers de configuration" in output
    assert "Rechargement de systemd" in output
    assert "✓ Configuration systemd rechargée." in output
    assert "Activation des services systemd" in output
    assert "✓ ohanna-agent.service activé." in output
    assert "✓ ohanna-vision.service activé." in output
    assert "Démarrage des services systemd" in output
    assert "ohanna-agent.service démarré" in output
    assert "ohanna-vision.service démarré" in output
    assert "Vérification des services systemd" in output
    assert "ohanna-agent.service est actif" in output
    assert "ohanna-vision.service est actif" in output
    assert (
        "Ohanna-Agent et Ohanna-Vision sont installés, "
        "configurés, activés et démarrés."
    ) in output


def test_install_fails_when_component_download_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    def raise_download_error(
        manifest: PlatformManifest,
        directory: Path,
    ) -> tuple[DownloadedComponent, ...]:
        del manifest
        del directory

        raise DownloadError("wheel introuvable")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        raise_download_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Téléchargement impossible" in output
    assert "wheel introuvable" in output


def test_install_fails_when_agent_installation_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    def raise_installation_error(
        downloaded_components: tuple[DownloadedComponent, ...],
    ) -> InstalledPythonComponent:
        del downloaded_components

        raise PackageInstallationError("échec de pip")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        raise_installation_error,
    )

    vision_installation_called = False

    def install_vision(
        downloaded_components: tuple[DownloadedComponent, ...],
    ) -> InstalledPythonComponent:
        del downloaded_components

        nonlocal vision_installation_called
        vision_installation_called = True

        return _build_installed_vision()

    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        install_vision,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Installation impossible" in output
    assert "échec de pip" in output
    assert vision_installation_called is False


def test_install_agent_creates_environment_and_installs_wheel(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = _build_manifest()

    agent = next(
        component
        for component in manifest.components
        if component.identifier == "agent"
    )

    wheel_path = tmp_path / agent.package.filename

    downloaded_components = (
        DownloadedComponent(
            component=agent,
            path=wheel_path,
        ),
    )

    created_environment: Path | None = None
    installed_wheel: Path | None = None

    def fake_create_virtual_environment(
        environment_path: Path,
    ) -> Path:
        nonlocal created_environment
        created_environment = environment_path

        return environment_path

    def fake_install_wheel(
        package_path: Path,
        environment_path: Path,
    ) -> None:
        nonlocal installed_wheel
        installed_wheel = package_path

        assert environment_path == Path(
            "/opt/ohanna-agent/venv"
        )

    expected_component = _build_installed_agent()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.create_virtual_environment",
        fake_create_virtual_environment,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install.install_wheel",
        fake_install_wheel,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install.verify_component_command",
        lambda **kwargs: expected_component,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    from ohanna_installer.commands.install import _install_agent

    result = _install_agent(downloaded_components)

    assert created_environment == Path(
        "/opt/ohanna-agent/venv"
    )
    assert installed_wheel == wheel_path
    assert result == expected_component

def test_install_fails_when_systemd_reload_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: (),
    )

    def raise_reload_error() -> None:
        raise SystemdCommandError("daemon-reload refusé")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        raise_reload_error,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Commande systemd impossible" in output
    assert "daemon-reload refusé" in output

def test_install_agent_fails_when_agent_was_not_downloaded() -> None:
    manifest = _build_manifest()

    vision = next(
        component
        for component in manifest.components
        if component.identifier == "vision"
    )

    downloaded_components = (
        DownloadedComponent(
            component=vision,
            path=Path(vision.package.filename),
        ),
    )

    from ohanna_installer.commands.install import _install_agent

    with pytest.raises(
        PackageInstallationError,
        match="agent est absent",
    ):
        _install_agent(downloaded_components)

def _build_installed_vision() -> InstalledPythonComponent:
    return InstalledPythonComponent(
        name="Ohanna-Vision",
        version="1.0.0",
        environment_path=Path("/opt/ohanna-vision/venv"),
        executable_path=Path(
            "/opt/ohanna-vision/venv/bin/ohanna-vision"
        ),
    )

def test_install_fails_when_vision_installation_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )

    def raise_installation_error(
        downloaded_components: tuple[DownloadedComponent, ...],
    ) -> InstalledPythonComponent:
        del downloaded_components

        raise PackageInstallationError("échec de Vision")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        raise_installation_error,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "✓ Ohanna-Agent 1.0.0 installé." in output
    assert "Installation d'Ohanna-Vision" in output
    assert "Installation impossible" in output
    assert "échec de Vision" in output

def test_install_vision_creates_environment_and_installs_wheel(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manifest = _build_manifest()

    vision = next(
        component
        for component in manifest.components
        if component.identifier == "vision"
    )

    wheel_path = tmp_path / vision.package.filename

    downloaded_components = (
        DownloadedComponent(
            component=vision,
            path=wheel_path,
        ),
    )

    created_environment: Path | None = None
    installed_wheel: Path | None = None
    verification_arguments: dict[str, object] | None = None

    def fake_create_virtual_environment(
        environment_path: Path,
    ) -> Path:
        nonlocal created_environment
        created_environment = environment_path

        return environment_path

    def fake_install_wheel(
        package_path: Path,
        environment_path: Path,
    ) -> None:
        nonlocal installed_wheel
        installed_wheel = package_path

        assert environment_path == Path(
            "/opt/ohanna-vision/venv"
        )

    def fake_verify_component_command(
        **kwargs: object,
    ) -> InstalledPythonComponent:
        nonlocal verification_arguments
        verification_arguments = kwargs

        return _build_installed_vision()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.create_virtual_environment",
        fake_create_virtual_environment,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install.install_wheel",
        fake_install_wheel,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install.verify_component_command",
        fake_verify_component_command,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    from ohanna_installer.commands.install import _install_vision

    result = _install_vision(downloaded_components)

    assert created_environment == Path(
        "/opt/ohanna-vision/venv"
    )
    assert installed_wheel == wheel_path
    assert verification_arguments == {
        "environment_path": Path("/opt/ohanna-vision/venv"),
        "command_name": "ohanna-vision",
        "expected_version": "1.0.0",
        "component_name": "Ohanna-Vision",
    }
    assert result == _build_installed_vision()

def test_install_vision_fails_when_vision_was_not_downloaded() -> None:
    manifest = _build_manifest()

    agent = next(
        component
        for component in manifest.components
        if component.identifier == "agent"
    )

    downloaded_components = (
        DownloadedComponent(
            component=agent,
            path=Path(agent.package.filename),
        ),
    )

    from ohanna_installer.commands.install import _install_vision

    with pytest.raises(
        PackageInstallationError,
        match="vision est absent",
    ):
        _install_vision(downloaded_components)

def test_install_fails_when_systemd_installation_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    def raise_systemd_error(
        generated_services: tuple[GeneratedSystemdService, ...],
    ) -> tuple[InstalledSystemdService, ...]:
        del generated_services
        raise SystemdInstallationError(
            "permission refusée"
        )

    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        raise_systemd_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Installation systemd impossible" in output
    assert "permission refusée" in output

def test_install_fails_when_systemd_enable_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )

    def raise_enable_error(
        installed_services: tuple[InstalledSystemdService, ...],
    ) -> None:
        del installed_services
        raise SystemdCommandError(
            "activation refusée"
        )

    monkeypatch.setattr(
        "ohanna_installer.commands.install._enable_services",
        raise_enable_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Commande systemd impossible" in output
    assert "activation refusée" in output

def test_install_fails_when_systemd_start_fails(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._enable_services",
        lambda installed_services: None,
    )

    def raise_start_error(
        installed_services: tuple[InstalledSystemdService, ...],
    ) -> None:
        del installed_services
        raise SystemdCommandError("démarrage refusé")

    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        raise_start_error,
    )

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Démarrage des services systemd" in output
    assert "Commande systemd impossible" in output
    assert "démarrage refusé" in output

def test_install_fails_when_service_is_not_active(
    monkeypatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    manifest = _build_manifest()

    monkeypatch.setattr(
        "ohanna_installer.commands.install.run_environment_checks",
        lambda: (
            EnvironmentCheck(
                name="Linux",
                success=True,
                message="Compatible.",
            ),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._load_official_manifest",
        lambda directory: manifest,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._download_components",
        _build_downloaded_components,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_agent",
        lambda downloaded_components: _build_installed_agent(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_vision",
        lambda downloaded_components: _build_installed_vision(),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._generate_services",
        lambda manifest, directory: (),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._install_services",
        lambda generated_services: _build_installed_services(
            manifest,
            Path("/tmp/systemd"),
        ),
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._reload_systemd",
        lambda: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._enable_services",
        lambda installed_services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._start_services",
        lambda installed_services: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.commands.install._check_services",
        lambda installed_services: (
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

    assert main(["install"]) == 3

    output = capsys.readouterr().out

    assert "Vérification des services systemd" in output
    assert "ohanna-agent.service est failed" in output
    assert "ohanna-vision.service est actif" not in output
