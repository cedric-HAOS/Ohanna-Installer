"""Tests de gestion des comptes système Ohanna."""

import subprocess
from pathlib import Path

import pytest

from ohanna_installer.system_account import (
    SystemAccountError,
    ensure_system_account,
)


def test_ensure_system_account_accepts_existing_compatible_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_group_gid",
        lambda group_name: 991,
    )
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_user_primary_gid",
        lambda username: 991,
    )

    commands: list[list[str]] = []
    monkeypatch.setattr(
        "ohanna_installer.system_account._run_account_command",
        lambda command, **kwargs: commands.append(command),
    )

    account = ensure_system_account("ohanna", "ohanna")

    assert account.username == "ohanna"
    assert account.group_name == "ohanna"
    assert account.user_created is False
    assert account.group_created is False
    assert commands == []


def test_ensure_system_account_creates_group_and_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    group_gids = iter((None, 991))
    user_gids = iter((None, 991))

    monkeypatch.setattr(
        "ohanna_installer.system_account._get_group_gid",
        lambda group_name: next(group_gids),
    )
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_user_primary_gid",
        lambda username: next(user_gids),
    )
    monkeypatch.setattr(
        "ohanna_installer.system_account._resolve_nologin_shell",
        lambda: Path("/sbin/nologin"),
    )

    commands: list[tuple[list[str], float, str]] = []

    def capture_command(
        command: list[str],
        *,
        timeout: float,
        description: str,
    ) -> None:
        commands.append((command, timeout, description))

    monkeypatch.setattr(
        "ohanna_installer.system_account._run_account_command",
        capture_command,
    )

    account = ensure_system_account("ohanna", "ohanna")

    assert account.user_created is True
    assert account.group_created is True
    assert commands == [
        (
            ["groupadd", "--system", "ohanna"],
            30.0,
            "création du groupe système ohanna",
        ),
        (
            [
                "useradd",
                "--system",
                "--gid",
                "ohanna",
                "--home-dir",
                "/nonexistent",
                "--no-create-home",
                "--shell",
                "/sbin/nologin",
                "ohanna",
            ],
            30.0,
            "création du compte système ohanna",
        ),
    ]


def test_ensure_system_account_rejects_incompatible_primary_group(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_group_gid",
        lambda group_name: 991,
    )
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_user_primary_gid",
        lambda username: 992,
    )

    with pytest.raises(
        SystemAccountError,
        match="utilise le groupe primaire 992",
    ):
        ensure_system_account("ohanna", "ohanna")


def test_ensure_system_account_rejects_invalid_names() -> None:
    with pytest.raises(
        SystemAccountError,
        match="Nom de utilisateur système invalide",
    ):
        ensure_system_account("--root", "ohanna")

    with pytest.raises(
        SystemAccountError,
        match="Nom de groupe système invalide",
    ):
        ensure_system_account("ohanna", "../wheel")


def test_ensure_system_account_requires_created_group_to_exist(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "ohanna_installer.system_account._get_group_gid",
        lambda group_name: None,
    )
    monkeypatch.setattr(
        "ohanna_installer.system_account._run_account_command",
        lambda command, **kwargs: None,
    )

    with pytest.raises(
        SystemAccountError,
        match="reste introuvable après sa création",
    ):
        ensure_system_account("ohanna", "ohanna")


def test_account_command_reports_command_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ohanna_installer.system_account import _run_account_command

    def raise_command_error(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        raise subprocess.CalledProcessError(
            returncode=9,
            cmd=command,
            stderr="permission denied",
        )

    monkeypatch.setattr(
        "ohanna_installer.system_account.subprocess.run",
        raise_command_error,
    )

    with pytest.raises(
        SystemAccountError,
        match="permission denied",
    ):
        _run_account_command(
            ["groupadd", "--system", "ohanna"],
            timeout=30.0,
            description="création du groupe système ohanna",
        )


def test_account_command_reports_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ohanna_installer.system_account import _run_account_command

    def raise_timeout(
        command: list[str],
        **kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        del kwargs
        raise subprocess.TimeoutExpired(command, 30.0)

    monkeypatch.setattr(
        "ohanna_installer.system_account.subprocess.run",
        raise_timeout,
    )

    with pytest.raises(
        SystemAccountError,
        match="délai autorisé",
    ):
        _run_account_command(
            ["useradd", "ohanna"],
            timeout=30.0,
            description="création du compte système ohanna",
        )


def test_ensure_service_accounts_deduplicates_manifest_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from ohanna_installer.commands.install import _ensure_service_accounts
    from ohanna_installer.manifest import (
        CompatibilityManifest,
        ComponentManifest,
        ComponentPackage,
        ComponentService,
        PlatformManifest,
        RuntimeManifest,
    )
    from ohanna_installer.system_account import SystemAccount

    def component(identifier: str) -> ComponentManifest:
        return ComponentManifest(
            identifier=identifier,
            name=f"Ohanna-{identifier.title()}",
            repository=f"cedric-HAOS/Ohanna-{identifier.title()}",
            version="1.1.0",
            release_tag="v1.1.0",
            package=ComponentPackage(
                type="wheel",
                filename=f"{identifier}-1.1.0.whl",
            ),
            service=ComponentService(
                filename=f"ohanna-{identifier}.service",
                description=identifier,
                user="ohanna",
                group="ohanna",
                working_directory=Path(f"/opt/ohanna-{identifier}"),
                executable=Path(f"/opt/ohanna-{identifier}/bin/app"),
                arguments=(),
            ),
        )

    manifest = PlatformManifest(
        schema_version=1,
        platform_name="Ohanna",
        platform_version="1.0.0",
        runtime=RuntimeManifest(
            minimum_python_version="3.12",
        ),
        components=(component("agent"), component("vision")),
        compatibility=CompatibilityManifest(
            operating_system_family="Linux",
            service_manager="systemd",
        ),
    )

    calls: list[tuple[str, str]] = []

    def fake_ensure_system_account(
        username: str,
        group_name: str,
    ) -> SystemAccount:
        calls.append((username, group_name))
        return SystemAccount(
            username=username,
            group_name=group_name,
            user_created=False,
            group_created=False,
        )

    monkeypatch.setattr(
        "ohanna_installer.commands.install.ensure_system_account",
        fake_ensure_system_account,
    )

    accounts = _ensure_service_accounts(manifest)

    assert len(accounts) == 1
    assert calls == [("ohanna", "ohanna")]
