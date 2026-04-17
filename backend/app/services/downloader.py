from __future__ import annotations

import asyncio
import json
import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from backend.app.config import Settings


@dataclass(frozen=True)
class ManifestSource:
    kind: str
    id: str
    url: str
    title: str
    channel: str | None
    playlist_id: str | None
    video_count: int


@dataclass(frozen=True)
class ManifestVideo:
    id: str
    url: str
    title: str
    channel: str | None
    duration_sec: float | None
    playlist_id: str | None


@dataclass(frozen=True)
class Manifest:
    kind: str
    source: ManifestSource
    videos: list[ManifestVideo]

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "Manifest":
        source = payload["source"]
        videos = payload.get("videos") or []
        return cls(
            kind=payload["kind"],
            source=ManifestSource(
                kind=source["kind"],
                id=source["id"],
                url=source["url"],
                title=source["title"],
                channel=source.get("channel"),
                playlist_id=source.get("playlistId") or source.get("playlist_id"),
                video_count=int(source.get("videoCount") or source.get("video_count") or 0),
            ),
            videos=[
                ManifestVideo(
                    id=item["id"],
                    url=item["url"],
                    title=item["title"],
                    channel=item.get("channel"),
                    duration_sec=item.get("durationSec", item.get("duration_sec")),
                    playlist_id=item.get("playlistId") or item.get("playlist_id"),
                )
                for item in videos
            ],
        )


@dataclass(frozen=True)
class DownloadedAudio:
    audio_path: Path
    container: str
    bitrate: str | None

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "DownloadedAudio":
        return cls(
            audio_path=Path(payload["audioPath"] or payload["audio_path"]),
            container=payload.get("container") or "",
            bitrate=payload.get("bitrate"),
        )


class DownloaderClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def inspect(self, url: str) -> Manifest:
        payload = await self._run_json(["inspect", "--url", url])
        return Manifest.from_payload(payload)

    async def download_audio(self, *, url: str, output_dir: Path, basename: str) -> DownloadedAudio:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = await self._run_json(
            [
                "download-audio",
                "--url",
                url,
                "--output-dir",
                str(output_dir),
                "--basename",
                basename,
            ]
        )
        return DownloadedAudio.from_payload(payload)

    async def _run_json(self, args: list[str]) -> dict[str, Any]:
        command = self._command_prefix() + args
        try:
            proc = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "Downloader sidecar could not start. Install .NET SDK 10+ or set DOWNLOADER_BIN."
            ) from exc

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=self.settings.downloader_timeout_sec
            )
        except TimeoutError as exc:
            proc.kill()
            await proc.communicate()
            raise RuntimeError("Downloader sidecar timed out.") from exc

        stdout_text = stdout.decode("utf-8", errors="replace").strip()
        stderr_text = stderr.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            detail = stderr_text or stdout_text or "no details"
            raise RuntimeError(f"Downloader sidecar failed: {detail}")
        try:
            return json.loads(stdout_text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Downloader returned invalid JSON: {stdout_text[:500]}") from exc

    def _command_prefix(self) -> list[str]:
        """Resolve the downloader executable command. Reads DOWNLOADER_BIN when configured and returns the process prefix argv."""
        configured = os.environ.get("DOWNLOADER_BIN")
        if configured:
            return [configured.strip().strip('"').strip("'")]
        dotnet = _find_dotnet()
        if self.settings.downloader_dll.exists():
            return [dotnet, str(self.settings.downloader_dll)]
        return [dotnet, "run", "--project", str(self.settings.downloader_project), "--"]


def _find_dotnet() -> str:
    configured = os.environ.get("DOTNET_EXE")
    if configured:
        return configured

    from_path = shutil.which("dotnet")
    if from_path:
        return from_path

    candidates = [
        Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "dotnet" / "dotnet.exe",
        Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "dotnet" / "dotnet.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return "dotnet"
