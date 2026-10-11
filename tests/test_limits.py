import pytest

from cvmatch.ingestion import read_bytes
from cvmatch.limits import InputTooLarge, Limits, UsageGuard, check_sizes


def test_check_sizes():
    lim = Limits(max_cv_chars=10, max_offer_chars=5)
    check_sizes("a" * 10, "b" * 5, lim)
    with pytest.raises(InputTooLarge, match="CV"):
        check_sizes("a" * 11, "b", lim)
    with pytest.raises(InputTooLarge, match="Offre"):
        check_sizes("a", "b" * 6, lim)


def test_usage_guard_hourly_window_and_daily_cap():
    now = [1_000_000.0]
    guard = UsageGuard(Limits(per_client_per_hour=2, per_day=3), clock=lambda: now[0])
    assert guard.acquire("a") is None and guard.acquire("a") is None
    assert "par heure" in guard.acquire("a")
    assert guard.acquire("b") is None  # autre client : sa propre fenêtre
    assert "quotidien" in guard.acquire("c")  # plafond global atteint (3)
    now[0] += 86_400  # lendemain : compteurs remis à zéro
    assert guard.acquire("a") is None


def test_read_bytes_text_and_pdf_page_limit():
    assert read_bytes("Expérience Python".encode(), "cv.md") == "Expérience Python"
    pypdf = pytest.importorskip("pypdf")
    import io

    writer = pypdf.PdfWriter()
    for _ in range(3):
        writer.add_blank_page(width=100, height=100)
    buf = io.BytesIO()
    writer.write(buf)
    with pytest.raises(InputTooLarge, match="3 pages"):
        read_bytes(buf.getvalue(), "cv.pdf", max_pages=2)
    assert read_bytes(buf.getvalue(), "cv.pdf", max_pages=3).strip() == ""
