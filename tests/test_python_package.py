"""Tests de l'installation des packages Python."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ohanna_installer.python_package import (
    PackageInstallationError,
    create_virtual_environment,
    get_environment_executable,
    install_wheel,
    verify_component_command,
)


def test_create_virtual_environment_runs_python_venv(
    tmp_path: Path,
    monkeypatch,
) -> None:
    environment_path = tmp_path / "venv"
    received_command: list[str] | None = None

    def fake_run_command(
        command: list[str],
        *,
        timeout: float,
        error_message: str,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal received_command

        received_command = command

        assert timeout == 120.0
        assert "Impossible de créer" in error_message

        environment_path.mkdir()

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.python_package._run_command",
        fake_run_command,
    )

    result = create_virtual_environment(
        environment_path,
        python_executable="/usr/bin/python3",
    )

    assert result == environment_path
    assert received_command == [
        "/usr/bin/python3",
        "-m",
        "venv",
        str(environment_path),
    ]


def test_create_virtual_environment_rejects_existing_path(
    tmp_path: Path,
) -> None:
    environment_path = tmp_path / "venv"
    environment_path.mkdir()

    with pytest.raises(
        PackageInstallationError,
        match="existe déjà",
    ):
        create_virtual_environment(environment_path)


def test_install_wheel_runs_environment_pip(
    tmp_path: Path,
    monkeypatch,
) -> None:
    environment_path = tmp_path / "venv"
    wheel_path = tmp_path / "ohanna_agent.whl"
    wheel_path.write_bytes(b"wheel")

    pip_path = get_environment_executable(
        environment_path,
        "pip",
    )
    pip_path.parent.mkdir(parents=True)
    pip_path.write_text("", encoding="utf-8")

    received_command: list[str] | None = None

    def fake_run_command(
        command: list[str],
        *,
        timeout: float,
        error_message: str,
    ) -> subprocess.CompletedProcess[str]:
        nonlocal received_command

        received_command = command

        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.python_package._run_command",
        fake_run_command,
    )

    install_wheel(
        wheel_path,
        environment_path,
    )

    assert received_command == [
        str(pip_path),
        "install",
        "--disable-pip-version-check",
        str(wheel_path),
    ]


def test_install_wheel_rejects_missing_file(
    tmp_path: Path,
) -> None:
    with pytest.raises(
        PackageInstallationError,
        match="wheel est introuvable",
    ):
        install_wheel(
            tmp_path / "missing.whl",
            tmp_path / "venv",
        )


def test_verify_component_command_accepts_expected_version(
    tmp_path: Path,
    monkeypatch,
) -> None:
    environment_path = tmp_path / "venv"
    executable_path = get_environment_executable(
        environment_path,
        "ohanna-agent",
    )
    executable_path.parent.mkdir(parents=True)
    executable_path.write_text("", encoding="utf-8")

    def fake_run_command(
        command: list[str],
        *,
        timeout: float,
        error_message: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="ohanna-agent 1.0.0\n",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.python_package._run_command",
        fake_run_command,
    )

    result = verify_component_command(
        environment_path=environment_path,
        command_name="ohanna-agent",
        expected_version="1.0.0",
        component_name="Ohanna-Agent",
    )

    assert result.name == "Ohanna-Agent"
    assert result.version == "1.0.0"
    assert result.executable_path == executable_path


def test_verify_component_command_rejects_unexpected_version(
    tmp_path: Path,
    monkeypatch,
) -> None:
    environment_path = tmp_path / "venv"
    executable_path = get_environment_executable(
        environment_path,
        "ohanna-agent",
    )
    executable_path.parent.mkdir(parents=True)
    executable_path.write_text("", encoding="utf-8")

    def fake_run_command(
        command: list[str],
        *,
        timeout: float,
        error_message: str,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            command,
            returncode=0,
            stdout="ohanna-agent 0.9.0\n",
            stderr="",
        )

    monkeypatch.setattr(
        "ohanna_installer.python_package._run_command",
        fake_run_command,
    )

    with pytest.raises(
        PackageInstallationError,
        match="Version inattendue",
    ):
        verify_component_command(
            environment_path=environment_path,
            command_name="ohanna-agent",
            expected_version="1.0.0",
            component_name="Ohanna-Agent",
        )