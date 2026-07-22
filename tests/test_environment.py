"""Tests de vérification de l'environnement."""

from __future__ import annotations

import sys
import urllib.error
from unittest.mock import MagicMock

from ohanna_installer.environment import (
    check_administrator,
    check_github_connectivity,
    check_linux,
    check_pip,
    check_python_version,
    check_systemd,
    run_environment_checks,
)


def test_check_linux_succeeds_on_linux(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Linux")

    result = check_linux()

    assert result.success is True
    assert result.name == "Système d'exploitation"
    assert result.message == "Linux détecté."


def test_check_linux_fails_on_unsupported_system(monkeypatch) -> None:
    monkeypatch.setattr("platform.system", lambda: "Windows")

    result = check_linux()

    assert result.success is False
    assert "Windows" in result.message


def test_check_systemd_succeeds_when_systemctl_exists(monkeypatch) -> None:
    monkeypatch.setattr(
        "ohanna_installer.environment.shutil.which",
        lambda command: "/usr/bin/systemctl" if command == "systemctl" else None,
    )

    result = check_systemd()

    assert result.success is True
    assert "/usr/bin/systemctl" in result.message


def test_check_systemd_fails_when_systemctl_is_missing(monkeypatch) -> None:
    monkeypatch.setattr(
        "ohanna_installer.environment.shutil.which",
        lambda command: None,
    )

    result = check_systemd()

    assert result.success is False
    assert "introuvable" in result.message


def test_check_python_version_succeeds_with_supported_version(
    monkeypatch,
) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 12, 4))

    result = check_python_version()

    assert result.success is True
    assert "3.12.4" in result.message


def test_check_python_version_fails_with_unsupported_version(
    monkeypatch,
) -> None:
    monkeypatch.setattr(sys, "version_info", (3, 11, 9))

    result = check_python_version()

    assert result.success is False
    assert "3.12" in result.message


def test_check_pip_succeeds() -> None:
    result = check_pip()

    assert result.success is True


def test_check_administrator_succeeds_for_root(monkeypatch) -> None:
    monkeypatch.setattr(
        "ohanna_installer.environment.os.geteuid",
        lambda: 0,
        raising=False,
    )

    result = check_administrator()

    assert result.success is True


def test_check_administrator_fails_for_standard_user(monkeypatch) -> None:
    monkeypatch.setattr(
        "ohanna_installer.environment.os.geteuid",
        lambda: 1000,
        raising=False,
    )

    result = check_administrator()

    assert result.success is False
    assert "sudo" in result.message


def test_check_github_connectivity_succeeds(monkeypatch) -> None:
    response = MagicMock()
    response.status = 200
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohanna_installer.environment.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    result = check_github_connectivity()

    assert result.success is True


def test_check_github_connectivity_fails(monkeypatch) -> None:
    def raise_url_error(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(
        "ohanna_installer.environment.urllib.request.urlopen",
        raise_url_error,
    )

    result = check_github_connectivity()

    assert result.success is False
    assert "connection refused" in result.message


def test_run_environment_checks_returns_all_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        "ohanna_installer.environment.check_linux",
        lambda: MagicMock(success=True),
    )
    monkeypatch.setattr(
        "ohanna_installer.environment.check_systemd",
        lambda: MagicMock(success=True),
    )
    monkeypatch.setattr(
        "ohanna_installer.environment.check_python_version",
        lambda: MagicMock(success=True),
    )
    monkeypatch.setattr(
        "ohanna_installer.environment.check_pip",
        lambda: MagicMock(success=True),
    )
    monkeypatch.setattr(
        "ohanna_installer.environment.check_administrator",
        lambda: MagicMock(success=True),
    )
    monkeypatch.setattr(
        "ohanna_installer.environment.check_github_connectivity",
        lambda: MagicMock(success=True),
    )

    results = run_environment_checks()

    assert len(results) == 6