"""Lecture d'un document (txt, md, pdf) et découpage du CV en chunks."""

from __future__ import annotations

from pathlib import Path

from .limits import InputTooLarge
from .schemas import CVChunk


def read_document(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    return read_bytes(p.read_bytes(), p.name)


def read_bytes(data: bytes, filename: str, max_pages: int | None = None) -> str:
    """Texte d'un fichier reçu en mémoire (upload web). `max_pages` borne la lecture des PDF."""
    if filename.lower().endswith(".pdf"):
        from io import BytesIO

        from pypdf import PdfReader

        reader = PdfReader(BytesIO(data))
        if max_pages is not None and len(reader.pages) > max_pages:
            raise InputTooLarge(f"PDF trop long : {len(reader.pages)} pages (maximum {max_pages}).")
        return "\n".join((page.extract_text() or "") for page in reader.pages)
    return data.decode("utf-8", errors="replace")


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if s.startswith("#"):
        return True
    # Titre de section en MAJUSCULES (cas fréquent dans les PDF extraits)
    return len(s) <= 40 and s.isupper() and any(c.isalpha() for c in s)


def chunk_cv(text: str, max_chars: int = 700) -> list[CVChunk]:
    """Découpe le CV en blocs cohérents (une expérience, un projet, une ligne de compétences).

    Un bloc = lignes consécutives sans ligne vide ; un titre de section démarre une nouvelle
    section ; un bloc trop long est coupé par groupes de lignes.
    """
    section = "En-tête"
    blocks: list[tuple[str, list[str]]] = []
    current: list[str] = []

    def flush() -> None:
        nonlocal current
        if current:
            blocks.append((section, current))
            current = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if _is_heading(line):
            flush()
            section = line.strip().lstrip("#").strip().strip(":").strip() or section
            continue
        if not line.strip():
            flush()
            continue
        current.append(line.strip())
    flush()

    chunks: list[CVChunk] = []

    def emit(sec: str, lines: list[str]) -> None:
        body = "\n".join(lines).strip()
        if body:
            chunks.append(CVChunk(id=f"c{len(chunks) + 1:02d}", section=sec, text=body))

    for sec, lines in blocks:
        buf: list[str] = []
        size = 0
        for ln in lines:
            if buf and size + len(ln) > max_chars:
                emit(sec, buf)
                buf, size = [], 0
            buf.append(ln)
            size += len(ln) + 1
        emit(sec, buf)
    return chunks
