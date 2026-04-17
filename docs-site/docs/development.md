---
sidebar_position: 8
title: Development
---

# Development

## Useful Commands

```powershell
.\.venv\Scripts\python.exe -m pytest backend\tests
cmd /c npm run build --prefix frontend
cmd /c npm run build --prefix docs-site
dotnet build downloader\YoutubeNoteDownloader\YoutubeNoteDownloader.csproj
```

## Code Organization

Backend route handlers are grouped by product area. Shared service construction lives in `backend/app/dependencies.py`, while durable data access stays in `backend/app/database.py`.

Frontend code is split by responsibility:

- `App.tsx`: top-level shell, theme, and tabs.
- `api.ts`: fetch helpers.
- `types.ts`: shared API shapes.
- `constants.ts`: frontend constants.
- `views/`: product workspaces.
- `styles/`: CSS split by shared base and workspace-specific rules.

## Documentation Site

The documentation is a Docusaurus site under `docs-site/`. Start it locally:

```powershell
.\scripts\start-docs.ps1
```

Build static documentation:

```powershell
.\scripts\build-docs.ps1
```
