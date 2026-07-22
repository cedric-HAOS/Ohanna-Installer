"""Tests de génération des unités systemd."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ohanna_installer.manifest import (
    ComponentManifest,
    ComponentPackage,
    ComponentService,
)
from ohanna_installer.systemd import (
    GeneratedSystemdService,
    SystemdCommandError,
    SystemdGenerationError,
    SystemdInstallationError,
    enable_systemd_service,
    enable_systemd_services,
    generate_component_service,
    generate_systemd_services,
    install_generated_service,
    install_generated_services,
    reload_systemd_daemon,
    render_systemd_service,
)


def test_enable_systemd_service_runs_expected_command(
    monkeypatch,
) -> None:
    received_command: list[str] | None = None

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal received_command
        received_command = command

        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 30.0

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        fake_run,
    )

    enable_systemd_service("ohanna-agent.service")

    assert received_command == [
        "systemctl",
        "enable",
        "ohanna-agent.service",
    ]

def test_enable_systemd_service_rejects_invalid_name() -> None:
    with pytest.raises(
        SystemdCommandError,
        match="Nom de service systemd invalide",
    ):
        enable_systemd_service(
            "../ohanna-agent.service"
        )

def test_enable_systemd_service_requires_service_suffix() -> None:
    with pytest.raises(
        SystemdCommandError,
        match=r"doit se terminer par '\.service'",
    ):
        enable_systemd_service("ohanna-agent")

def test_enable_systemd_service_handles_command_error(
    monkeypatch,
) -> None:
    def raise_command_error(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs

        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            stderr="permission denied",
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        raise_command_error,
    )

    with pytest.raises(
        SystemdCommandError,
        match="permission denied",
    ):
        enable_systemd_service(
            "ohanna-agent.service"
        )

def test_enable_systemd_service_handles_timeout(
    monkeypatch,
) -> None:
    def raise_timeout(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs

        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=30.0,
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        raise_timeout,
    )

    with pytest.raises(
        SystemdCommandError,
        match="délai autorisé",
    ):
        enable_systemd_service(
            "ohanna-agent.service"
        )

def test_enable_systemd_services_enables_all_services(
    tmp_path: Path,
    monkeypatch,
) -> None:
    component = _build_component(
        service=_build_agent_service(),
    )

    generated_service = GeneratedSystemdService(
        component=component,
        path=tmp_path / "ohanna-agent.service",
        content="[Unit]\n",
    )

    installed_agent = InstalledSystemdService(
        component=component,
        source_path=generated_service.path,
        destination_path=(
            tmp_path / "systemd" / "ohanna-agent.service"
        ),
        created=True,
    )

    vision = _build_component(
        identifier="vision",
        name="Ohanna-Vision",
        service=ComponentService(
            filename="ohanna-vision.service",
            description="Ohanna Vision",
            user="ohanna",
            group="ohanna",
            working_directory=Path("/opt/ohanna-vision"),
            executable=Path(
                "/opt/ohanna-vision/venv/bin/ohanna-vision"
            ),
            arguments=(),
        ),
    )

    installed_vision = InstalledSystemdService(
        component=vision,
        source_path=tmp_path / "ohanna-vision.service",
        destination_path=(
            tmp_path / "systemd" / "ohanna-vision.service"
        ),
        created=True,
    )

    enabled_services: list[str] = []

    def fake_enable_systemd_service(
        service_name: str,
        *,
        systemctl_executable: Path | str,
        timeout: float,
    ) -> None:
        assert systemctl_executable == "systemctl"
        assert timeout == 30.0
        enabled_services.append(service_name)

    monkeypatch.setattr(
        "ohanna_installer.systemd.enable_systemd_service",
        fake_enable_systemd_service,
    )

    enable_systemd_services(
        (
            installed_agent,
            installed_vision,
        )
    )

    assert enabled_services == [
        "ohanna-agent.service",
        "ohanna-vision.service",
    ]

def _generate_agent_service(
    tmp_path: Path,
) -> GeneratedSystemdService:
    component = _build_component(
        service=_build_agent_service(),
    )

    return generate_component_service(
        component,
        tmp_path,
    )

def test_install_generated_service_copies_unit(
    tmp_path: Path,
) -> None:
    generated_directory = tmp_path / "generated"
    system_directory = tmp_path / "systemd"

    generated_service = _generate_agent_service(
        generated_directory,
    )

    result = install_generated_service(
        generated_service,
        system_directory=system_directory,
    )

    destination = (
        system_directory
        / "ohanna-agent.service"
    )

    assert result.created is True
    assert result.destination_path == destination
    assert destination.exists()
    assert destination.read_text(
        encoding="utf-8",
    ) == generated_service.content

def test_install_generated_service_accepts_identical_existing_unit(
    tmp_path: Path,
) -> None:
    generated_directory = tmp_path / "generated"
    system_directory = tmp_path / "systemd"

    generated_service = _generate_agent_service(
        generated_directory,
    )

    system_directory.mkdir()
    destination = (
        system_directory
        / "ohanna-agent.service"
    )
    destination.write_text(
        generated_service.content,
        encoding="utf-8",
        newline="\n",
    )

    result = install_generated_service(
        generated_service,
        system_directory=system_directory,
    )

    assert result.created is False
    assert result.destination_path == destination

def test_install_generated_service_rejects_different_existing_unit(
    tmp_path: Path,
) -> None:
    generated_directory = tmp_path / "generated"
    system_directory = tmp_path / "systemd"

    generated_service = _generate_agent_service(
        generated_directory,
    )

    system_directory.mkdir()
    destination = (
        system_directory
        / "ohanna-agent.service"
    )
    destination.write_text(
        "custom content\n",
        encoding="utf-8",
    )

    with pytest.raises(
        SystemdInstallationError,
        match="contenu différent",
    ):
        install_generated_service(
            generated_service,
            system_directory=system_directory,
        )

def test_install_generated_service_rejects_missing_source(
    tmp_path: Path,
) -> None:
    component = _build_component(
        service=_build_agent_service(),
    )

    generated_service = GeneratedSystemdService(
        component=component,
        path=tmp_path / "missing.service",
        content="[Unit]\n",
    )

    with pytest.raises(
        SystemdInstallationError,
        match="unité générée est introuvable",
    ):
        install_generated_service(
            generated_service,
            system_directory=tmp_path / "systemd",
        )

def test_install_generated_services_installs_all_units(
    tmp_path: Path,
) -> None:
    generated_directory = tmp_path / "generated"
    system_directory = tmp_path / "systemd"

    agent = _build_component(
        service=_build_agent_service(),
    )
    vision = _build_component(
        identifier="vision",
        name="Ohanna-Vision",
        service=ComponentService(
            filename="ohanna-vision.service",
            description="Ohanna Vision",
            user="ohanna",
            group="ohanna",
            working_directory=Path("/opt/ohanna-vision"),
            executable=Path(
                "/opt/ohanna-vision/venv/bin/ohanna-vision"
            ),
            arguments=(),
        ),
    )

    generated_services = generate_systemd_services(
        (agent, vision),
        generated_directory,
    )

    results = install_generated_services(
        generated_services,
        system_directory=system_directory,
    )

    assert len(results) == 2
    assert (
        system_directory / "ohanna-agent.service"
    ).exists()
    assert (
        system_directory / "ohanna-vision.service"
    ).exists()

def _build_component(
    *,
    identifier: str = "agent",
    name: str = "Ohanna-Agent",
    service: ComponentService | None = None,
) -> ComponentManifest:
    return ComponentManifest(
        identifier=identifier,
        name=name,
        repository=f"cedric-HAOS/{name}",
        version="1.0.0",
        release_tag="v1.0.0",
        package=ComponentPackage(
            type="wheel",
            filename=f"{identifier}-1.0.0.whl",
        ),
        service=service,
    )


def _build_agent_service() -> ComponentService:
    return ComponentService(
        filename="ohanna-agent.service",
        description="Ohanna Agent",
        user="ohanna",
        group="ohanna",
        working_directory=Path("/opt/ohanna-agent"),
        executable=Path(
            "/opt/ohanna-agent/venv/bin/ohanna-agent"
        ),
        arguments=(
            "--config",
            "/etc/ohanna-agent/shikamaru.yaml",
        ),
    )


def test_render_systemd_service() -> None:
    content = render_systemd_service(
        _build_agent_service()
    )

    assert "[Unit]" in content
    assert "Description=Ohanna Agent" in content
    assert "After=network-online.target" in content
    assert "User=ohanna" in content
    assert "Group=ohanna" in content
    assert "WorkingDirectory=/opt/ohanna-agent" in content
    assert (
        "ExecStart=/opt/ohanna-agent/venv/bin/ohanna-agent "
        "--config /etc/ohanna-agent/shikamaru.yaml"
    ) in content
    assert "Restart=on-failure" in content
    assert "NoNewPrivileges=true" in content
    assert "WantedBy=multi-user.target" in content
    assert content.endswith("\n")


def test_generate_component_service_writes_file(
    tmp_path: Path,
) -> None:
    component = _build_component(
        service=_build_agent_service(),
    )

    result = generate_component_service(
        component,
        tmp_path,
    )

    expected_path = tmp_path / "ohanna-agent.service"

    assert result.path == expected_path
    assert expected_path.exists()
    assert expected_path.read_text(
        encoding="utf-8"
    ) == result.content


def test_generate_component_service_rejects_missing_service(
    tmp_path: Path,
) -> None:
    component = _build_component(service=None)

    with pytest.raises(
        SystemdGenerationError,
        match="ne déclare aucun service",
    ):
        generate_component_service(
            component,
            tmp_path,
        )


def test_generate_systemd_services_generates_declared_services(
    tmp_path: Path,
) -> None:
    agent_service = _build_agent_service()

    vision_service = ComponentService(
        filename="ohanna-vision.service",
        description="Ohanna Vision",
        user="ohanna",
        group="ohanna",
        working_directory=Path("/opt/ohanna-vision"),
        executable=Path(
            "/opt/ohanna-vision/venv/bin/ohanna-vision"
        ),
        arguments=(),
    )

    agent = _build_component(
        service=agent_service,
    )
    vision = _build_component(
        identifier="vision",
        name="Ohanna-Vision",
        service=vision_service,
    )

    results = generate_systemd_services(
        (agent, vision),
        tmp_path,
    )

    assert len(results) == 2
    assert (
        tmp_path / "ohanna-agent.service"
    ).exists()
    assert (
        tmp_path / "ohanna-vision.service"
    ).exists()


def test_generate_systemd_services_ignores_component_without_service(
    tmp_path: Path,
) -> None:
    agent = _build_component(
        service=_build_agent_service(),
    )
    component_without_service = _build_component(
        identifier="other",
        name="Other",
        service=None,
    )

    results = generate_systemd_services(
        (agent, component_without_service),
        tmp_path,
    )

    assert len(results) == 1
    assert results[0].component.identifier == "agent"

def test_reload_systemd_daemon_runs_expected_command(
    monkeypatch,
) -> None:
    received_command: list[str] | None = None

    def fake_run(
        command: list[str],
        *,
        check: bool,
        capture_output: bool,
        text: bool,
        timeout: float,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal received_command
        received_command = command

        assert check is True
        assert capture_output is True
        assert text is True
        assert timeout == 30.0

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        fake_run,
    )

    reload_systemd_daemon()

    assert received_command == [
        "systemctl",
        "daemon-reload",
    ]

def test_reload_systemd_daemon_handles_command_error(
    monkeypatch,
) -> None:
    def raise_command_error(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs

        raise subprocess.CalledProcessError(
            returncode=1,
            cmd=command,
            stderr="access denied",
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        raise_command_error,
    )

    with pytest.raises(
        SystemdCommandError,
        match="access denied",
    ):
        reload_systemd_daemon()
    
def test_reload_systemd_daemon_handles_timeout(
    monkeypatch,
) -> None:
    def raise_timeout(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs

        raise subprocess.TimeoutExpired(
            cmd=command,
            timeout=30.0,
        )

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        raise_timeout,
    )

    with pytest.raises(
        SystemdCommandError,
        match="délai autorisé",
    ):
        reload_systemd_daemon()

def test_reload_systemd_daemon_handles_os_error(
    monkeypatch,
) -> None:
    def raise_os_error(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del command
        del kwargs

        raise OSError("systemctl introuvable")

    monkeypatch.setattr(
        "ohanna_installer.systemd.subprocess.run",
        raise_os_error,
    )

    with pytest.raises(
        SystemdCommandError,
        match="systemctl introuvable",
    ):
        reload_systemd_daemon()