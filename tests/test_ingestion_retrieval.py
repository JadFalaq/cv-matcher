import string

import numpy as np
import pytest

from cvmatch.ingestion import chunk_cv, read_document
from cvmatch.retrieval import HybridRetriever


def test_chunk_cv_sections_and_content(sample_cv):
    chunks = chunk_cv(sample_cv)
    ids = [c.id for c in chunks]
    assert len(set(ids)) == len(ids)
    assert {"Expérience", "Projets", "Compétences"} <= {c.section for c in chunks}
    joined = "\n".join(c.text for c in chunks)
    assert "FAISS" in joined and "MLflow" in joined and "Anglais (C1)" in joined


def test_chunk_cv_splits_long_blocks():
    text = "## Expérience\n" + "\n".join(f"- ligne {i} " + "x" * 80 for i in range(30))
    chunks = chunk_cv(text, max_chars=300)
    assert len(chunks) > 5
    assert all(len(c.text) <= 300 + 100 for c in chunks)


def test_chunk_cv_uppercase_headings_from_pdf_extraction():
    chunks = chunk_cv("EXPÉRIENCE\nStage chez X\n\nCOMPÉTENCES\nPython, Docker")
    assert [c.section for c in chunks] == ["EXPÉRIENCE", "COMPÉTENCES"]


def test_chunk_empty_cv():
    assert chunk_cv("") == []
    assert chunk_cv("   \n\n  ") == []


def test_bm25_retrieves_the_right_chunk(sample_cv):
    r = HybridRetriever(chunk_cv(sample_cv))
    hits = r.search("docker conteneurisation", k=2)
    assert "Docker" in hits[0][0].text


def test_query_expansion_finds_implicit_evidence(sample_cv):
    r = HybridRetriever(chunk_cv(sample_cv))
    hits = r.search("rest api api rest fastapi flask endpoints swagger", k=1)
    assert "FastAPI" in hits[0][0].text


def test_k_is_capped_and_empty_index_is_safe(sample_cv):
    chunks = chunk_cv(sample_cv)
    assert len(HybridRetriever(chunks).search("python", k=999)) == len(chunks)
    assert HybridRetriever([]).search("python") == []


def _letters_embedder(texts):
    return np.array([[t.lower().count(ch) for ch in string.ascii_lowercase] for t in texts], dtype=float)


def test_hybrid_fusion_with_embeddings(sample_cv):
    chunks = chunk_cv(sample_cv)
    r = HybridRetriever(chunks, embedder=_letters_embedder)
    hits = r.search("FAISS recherche sémantique", k=3, query_dense="faiss semantic search")
    assert len(hits) == 3
    assert "FAISS" in hits[0][0].text  # le lexical garde la main sur un terme rare


def _tiny_pdf(lines):
    """PDF minimal valide, fabriqué à la main (évite une dépendance de génération de PDF)."""
    content = "BT /F1 12 Tf 50 750 Td 14 TL " + " ".join(f"({ln}) Tj T*" for ln in lines) + " ET"
    objs = [
        "<< /Type /Catalog /Pages 2 0 R >>",
        "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n{content}\nendstream",
        "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = b"%PDF-1.4\n", []
    for i, obj in enumerate(objs, 1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n{obj}\nendobj\n".encode()
    xref = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode()
    return out


def test_read_pdf_then_chunk(tmp_path):
    pdf = tmp_path / "cv.pdf"
    pdf.write_bytes(_tiny_pdf(["COMPETENCES", "Python, Docker, Git", "EXPERIENCE", "Mise en place de MLflow et FastAPI"]))
    chunks = chunk_cv(read_document(pdf))
    assert [(c.section, c.text) for c in chunks] == [
        ("COMPETENCES", "Python, Docker, Git"),
        ("EXPERIENCE", "Mise en place de MLflow et FastAPI"),
    ]


def test_read_document_txt_and_missing(tmp_path):
    f = tmp_path / "cv.txt"
    f.write_text("Python — Docker", encoding="utf-8")
    assert read_document(f) == "Python — Docker"
    with pytest.raises(FileNotFoundError):
        read_document(tmp_path / "nope.pdf")
