from __future__ import annotations

import re
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup

from backend.app.services.chunker import estimate_tokens


@dataclass(frozen=True)
class TextChunk:
    chunk_index: int
    text: str
    token_estimate: int


@dataclass(frozen=True)
class ExtractedWebPage:
    title: str
    text: str


async def fetch_web_page_text(url: str) -> ExtractedWebPage:
    async with httpx.AsyncClient(
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "ContextStudio/0.1"},
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
    return extract_web_page_text(response.text, fallback_title=url)


def extract_web_page_text(html: str, *, fallback_title: str = "Web page") -> ExtractedWebPage:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "svg", "canvas", "nav", "footer", "header"]):
        tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        heading = soup.find(["h1", "h2"])
        title = heading.get_text(" ", strip=True) if heading else fallback_title

    text = soup.get_text("\n")
    lines = [line.strip() for line in text.splitlines()]
    compact = "\n".join(line for line in lines if line)
    compact = re.sub(r"\n{3,}", "\n\n", compact).strip()
    if not compact:
        raise ValueError("No readable text was found on this page.")
    return ExtractedWebPage(title=title[:240], text=compact)


def chunk_text(text: str, *, target_tokens: int = 900, overlap_tokens: int = 150) -> list[TextChunk]:
    paragraphs = [paragraph.strip() for paragraph in re.split(r"\n\s*\n", text) if paragraph.strip()]
    if not paragraphs:
        paragraphs = [text.strip()] if text.strip() else []

    chunks: list[TextChunk] = []
    current: list[str] = []
    current_tokens = 0

    for paragraph in paragraphs:
        paragraph_tokens = estimate_tokens(paragraph)
        if current and current_tokens + paragraph_tokens > target_tokens:
            chunks.append(_make_chunk(len(chunks), current))
            current = _overlap_tail(current, overlap_tokens)
            current_tokens = sum(estimate_tokens(item) for item in current)

        if paragraph_tokens > target_tokens and not current:
            for piece in _split_long_text(paragraph, target_tokens):
                chunks.append(_make_chunk(len(chunks), [piece]))
            continue

        current.append(paragraph)
        current_tokens += paragraph_tokens

    if current:
        chunks.append(_make_chunk(len(chunks), current))

    return chunks


def _make_chunk(index: int, parts: list[str]) -> TextChunk:
    text = "\n\n".join(parts).strip()
    return TextChunk(chunk_index=index, text=text, token_estimate=estimate_tokens(text))


def _overlap_tail(parts: list[str], overlap_tokens: int) -> list[str]:
    if overlap_tokens <= 0:
        return []
    selected: list[str] = []
    total = 0
    for part in reversed(parts):
        selected.append(part)
        total += estimate_tokens(part)
        if total >= overlap_tokens:
            break
    return list(reversed(selected))


def _split_long_text(text: str, target_tokens: int) -> list[str]:
    words = text.split()
    if not words:
        return []
    pieces: list[str] = []
    current: list[str] = []
    for word in words:
        current.append(word)
        if estimate_tokens(" ".join(current)) >= target_tokens:
            pieces.append(" ".join(current))
            current = []
    if current:
        pieces.append(" ".join(current))
    return pieces
