"""Interface Streamlit testée sans navigateur (AppTest), avec le LLM factice."""

import pytest

from tests.conftest import ROOT

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

APP = str(ROOT / "streamlit_app.py")


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.delenv("APP_ACCESS_CODE", raising=False)
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "1000")
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    return at


def analyze_sample(at):
    at.button[0].click().run()  # charger l'exemple
    next(b for b in at.button if b.label == "Analyser").click().run()
    assert not at.exception and not at.error
    return at


def metric(at, label):
    return next(m for m in at.metric if m.label == label).value


def test_full_flow_and_live_final_score(app):
    at = analyze_sample(app)
    assert metric(at, "Score actuel") == "44.5/100" and metric(at, "Avec tes choix") == "61.2/100"
    assert len(at.checkbox) == 5 and len(at.dataframe) == 1
    at.checkbox[0].uncheck().run()  # refuser une reformulation : le score final baisse, sans relancer l'analyse
    assert 44.5 < float(metric(at, "Avec tes choix").split("/")[0]) < 61.2


def test_empty_input_is_rejected(app):
    next(b for b in app.button if b.label == "Analyser").click().run()
    assert app.error and "Il faut un CV" in app.error[0].value


def test_rate_limit_message(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("RATE_LIMIT_PER_HOUR", "0")
    import streamlit as st

    st.cache_resource.clear()  # le compteur est partagé entre sessions : on repart de zéro
    at = AppTest.from_file(APP, default_timeout=60)
    at.run()
    at.button[0].click().run()
    next(b for b in at.button if b.label == "Analyser").click().run()
    assert at.warning and "par heure" in at.warning[0].value
    st.cache_resource.clear()
