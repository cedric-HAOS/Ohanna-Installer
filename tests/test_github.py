"""Tests du téléchargement des artefacts GitHub."""

from __future__ import annotations

import urllib.error
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from ohana_installer.github import (
    DownloadedComponent,
    DownloadedConfigurationFile,
    DownloadError,
    build_release_asset_url,
    download_component_configuration_files,
    download_component_package,
    download_component_packages,
    download_configuration_files,
    download_file,
    download_platform_manifest,
)
from ohana_installer.manifest import (
    ComponentConfiguration,
    ComponentManifest,
    ComponentPackage,
    ConfigurationFile,
    ManifestError,
)

VALID_MANIFEST_CONTENT = b"""
schema_version: 1

platform:
  name: Ohana
  version: "1.0.0"

runtime:
  python:
    minimum_version: "3.12"

components:
  agent:
    name: Ohana-Agent
    repository: cedric-HAOS/Ohana-Agent
    version: "1.0.0"
    release_tag: v1.0.0
    package:
      type: wheel
      filename: ohana_agent-1.0.0-py3-none-any.whl

  vision:
    name: Ohana-Vision
    repository: cedric-HAOS/Ohana-Vision
    version: "1.0.0"
    release_tag: v1.0.0
    package:
      type: wheel
      filename: ohana_vision-1.0.0-py3-none-any.whl

compatibility:
  operating_system:
    family: Linux
    service_manager: systemd
""".strip()


def test_build_release_asset_url() -> None:
    url = build_release_asset_url(
        repository="cedric-HAOS/Ohana-Platform",
        release_tag="v1.0.0",
        filename="release-manifest.yaml",
    )

    assert url == (
        "https://github.com/cedric-HAOS/Ohana-Platform/releases/download/"
        "v1.0.0/release-manifest.yaml"
    )


def test_download_file_writes_response_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    response = MagicMock()
    response.read.return_value = b"content"
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    destination = tmp_path / "artifact.txt"

    result = download_file(
        "https://example.invalid/artifact.txt",
        destination,
    )

    assert result == destination
    assert destination.read_bytes() == b"content"


def test_download_file_creates_parent_directories(
    tmp_path: Path,
    monkeypatch,
) -> None:
    response = MagicMock()
    response.read.return_value = b"content"
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    destination = tmp_path / "downloads" / "artifact.txt"

    download_file(
        "https://example.invalid/artifact.txt",
        destination,
    )

    assert destination.exists()


def test_download_file_rejects_empty_content(
    tmp_path: Path,
    monkeypatch,
) -> None:
    response = MagicMock()
    response.read.return_value = b""
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    destination = tmp_path / "artifact.txt"

    with pytest.raises(
        DownloadError,
        match="est vide",
    ):
        download_file(
            "https://example.invalid/artifact.txt",
            destination,
        )

    assert not destination.exists()


def test_download_file_handles_http_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def raise_http_error(request, timeout):
        raise urllib.error.HTTPError(
            url=request.full_url,
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        raise_http_error,
    )

    with pytest.raises(
        DownloadError,
        match="statut HTTP 404",
    ):
        download_file(
            "https://example.invalid/missing.txt",
            tmp_path / "missing.txt",
        )


def test_download_file_handles_network_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    def raise_url_error(request, timeout):
        raise urllib.error.URLError("connection refused")

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        raise_url_error,
    )

    with pytest.raises(
        DownloadError,
        match="connection refused",
    ):
        download_file(
            "https://example.invalid/artifact.txt",
            tmp_path / "artifact.txt",
        )


def test_download_platform_manifest_returns_valid_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    response = MagicMock()
    response.read.return_value = VALID_MANIFEST_CONTENT
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    destination = tmp_path / "release-manifest.yaml"

    manifest = download_platform_manifest(destination)

    assert destination.exists()
    assert manifest.platform_name == "Ohana"
    assert manifest.platform_version == "1.0.0"
    assert len(manifest.components) == 2


def test_download_platform_manifest_removes_invalid_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    response = MagicMock()
    response.read.return_value = b"invalid: [yaml"
    response.__enter__.return_value = response
    response.__exit__.return_value = False

    monkeypatch.setattr(
        "ohana_installer.github.urllib.request.urlopen",
        lambda request, timeout: response,
    )

    destination = tmp_path / "release-manifest.yaml"

    with pytest.raises(ManifestError):
        download_platform_manifest(destination)

    assert not destination.exists()

def _build_component(
    *,
    identifier: str = "agent",
    name: str = "Ohana-Agent",
    filename: str = "ohana_agent-1.0.0-py3-none-any.whl",
    configuration: ComponentConfiguration | None = None,
) -> ComponentManifest:
    return ComponentManifest(
        identifier=identifier,
        name=name,
        repository=f"cedric-HAOS/{name}",
        version="1.0.0",
        release_tag="v1.0.0",
        package=ComponentPackage(
            type="wheel",
            filename=filename,
        ),
        configuration=configuration,
    )

def test_download_component_package_downloads_wheel(
    tmp_path: Path,
    monkeypatch,
) -> None:
    component = _build_component()
    expected_path = tmp_path / component.package.filename

    def fake_download_file(
        url: str,
        destination: Path,
        *,
        timeout: float,
    ) -> Path:
        assert url == (
            "https://github.com/cedric-HAOS/Ohana-Agent/releases/"
            "download/v1.0.0/"
            "ohana_agent-1.0.0-py3-none-any.whl"
        )
        assert destination == expected_path
        assert timeout == 15.0

        destination.write_bytes(b"wheel-content")
        return destination

    monkeypatch.setattr(
        "ohana_installer.github.download_file",
        fake_download_file,
    )

    result = download_component_package(
        component,
        tmp_path,
    )

    assert isinstance(result, DownloadedComponent)
    assert result.component == component
    assert result.path == expected_path
    assert result.path.read_bytes() == b"wheel-content"


def test_download_component_packages_downloads_all_components(
    tmp_path: Path,
    monkeypatch,
) -> None:
    agent = _build_component()
    vision = _build_component(
        identifier="vision",
        name="Ohana-Vision",
        filename="ohana_vision-1.0.0-py3-none-any.whl",
    )

    downloaded_filenames: list[str] = []

    def fake_download_component_package(
        component: ComponentManifest,
        destination_directory: Path,
        *,
        timeout: float,
    ) -> DownloadedComponent:
        path = destination_directory / component.package.filename
        path.write_bytes(b"wheel-content")
        downloaded_filenames.append(component.package.filename)

        return DownloadedComponent(
            component=component,
            path=path,
        )

    monkeypatch.setattr(
        "ohana_installer.github.download_component_package",
        fake_download_component_package,
    )

    results = download_component_packages(
        (agent, vision),
        tmp_path,
    )

    assert len(results) == 2
    assert downloaded_filenames == [
        "ohana_agent-1.0.0-py3-none-any.whl",
        "ohana_vision-1.0.0-py3-none-any.whl",
    ]
    assert all(result.path.exists() for result in results)


def test_download_component_packages_stops_on_first_error(
    tmp_path: Path,
    monkeypatch,
) -> None:
    agent = _build_component()
    vision = _build_component(
        identifier="vision",
        name="Ohana-Vision",
        filename="ohana_vision-1.0.0-py3-none-any.whl",
    )

    attempted_components: list[str] = []

    def fake_download_component_package(
        component: ComponentManifest,
        destination_directory: Path,
        *,
        timeout: float,
    ) -> DownloadedComponent:
        del destination_directory
        del timeout

        attempted_components.append(component.identifier)

        if component.identifier == "agent":
            raise DownloadError("échec agent")

        raise AssertionError("Vision ne doit pas être téléchargé.")

    monkeypatch.setattr(
        "ohana_installer.github.download_component_package",
        fake_download_component_package,
    )

    with pytest.raises(DownloadError, match="échec agent"):
        download_component_packages(
            (agent, vision),
            tmp_path,
        )

    assert attempted_components == ["agent"]

def test_download_component_configuration_files_downloads_agent_files(
    tmp_path: Path,
    monkeypatch,
) -> None:
    component = _build_component(
        configuration=ComponentConfiguration(
            directory=Path("/etc/ohana-agent"),
            files=(
                ConfigurationFile(
                    source="shikamaru.yaml",
                    destination=Path("shikamaru.yaml"),
                ),
                ConfigurationFile(
                    source="dns.yaml",
                    destination=Path("plugins/dns.yaml"),
                ),
            ),
        )
    )

    downloaded_urls: list[str] = []

    def fake_download_file(
        url: str,
        destination: Path,
        *,
        timeout: float,
    ) -> Path:
        del timeout
        downloaded_urls.append(url)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text("content", encoding="utf-8")
        return destination

    monkeypatch.setattr(
        "ohana_installer.github.download_file",
        fake_download_file,
    )

    results = download_component_configuration_files(
        component,
        tmp_path,
    )

    assert len(results) == 2
    assert all(
        isinstance(result, DownloadedConfigurationFile)
        for result in results
    )
    assert results[0].path == (
        tmp_path
        / "configuration"
        / "agent"
        / "shikamaru.yaml"
    )
    assert downloaded_urls == [
        (
            "https://github.com/cedric-HAOS/Ohana-Agent/releases/"
            "download/v1.0.0/shikamaru.yaml"
        ),
        (
            "https://github.com/cedric-HAOS/Ohana-Agent/releases/"
            "download/v1.0.0/dns.yaml"
        ),
    ]


def test_download_component_configuration_files_ignores_component_without_configuration(
    tmp_path: Path,
) -> None:
    component = _build_component(configuration=None)

    results = download_component_configuration_files(
        component,
        tmp_path,
    )

    assert results == ()


def test_download_configuration_files_downloads_only_declared_configurations(
    tmp_path: Path,
    monkeypatch,
) -> None:
    agent = _build_component(
        configuration=ComponentConfiguration(
            directory=Path("/etc/ohana-agent"),
            files=(
                ConfigurationFile(
                    source="shikamaru.yaml",
                    destination=Path("shikamaru.yaml"),
                ),
            ),
        )
    )
    vision = _build_component(
        identifier="vision",
        name="Ohana-Vision",
        filename="ohana_vision-1.0.0-py3-none-any.whl",
        configuration=None,
    )

    def fake_download_component_configuration_files(
        component: ComponentManifest,
        destination_directory: Path,
        *,
        timeout: float,
    ) -> tuple[DownloadedConfigurationFile, ...]:
        del destination_directory
        del timeout

        if component.configuration is None:
            return ()

        configuration_file = component.configuration.files[0]

        return (
            DownloadedConfigurationFile(
                component=component,
                configuration_file=configuration_file,
                path=tmp_path / configuration_file.source,
            ),
        )

    monkeypatch.setattr(
        "ohana_installer.github.download_component_configuration_files",
        fake_download_component_configuration_files,
    )

    results = download_configuration_files(
        (agent, vision),
        tmp_path,
    )

    assert len(results) == 1
    assert results[0].component.identifier == "agent"