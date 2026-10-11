import pytest

from cvmatch.config import Settings
from cvmatch.fake_llm import RuleBasedLLM
from cvmatch.llm import LangChainLLM, get_chat_model, get_embedder, get_llm
from cvmatch.schemas import JudgeVerdict


class StubRunnable:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = 0

    def invoke(self, messages):
        self.calls += 1
        out = self.outputs.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


class StubChat:
    def __init__(self, outputs):
        self.runnable = StubRunnable(outputs)

    def with_structured_output(self, schema):
        return self.runnable


def call(llm):
    return llm.structured(JudgeVerdict, system="s", user="u", tag="judge")


def test_adapter_retries_transient_errors_and_validates_dicts():
    chat = StubChat([RuntimeError("timeout"), {"status": "absent"}])
    out = call(LangChainLLM(chat, max_retries=2))
    assert isinstance(out, JudgeVerdict) and out.status == "absent" and chat.runnable.calls == 2


def test_adapter_gives_up_after_max_retries():
    chat = StubChat([RuntimeError("a"), RuntimeError("b"), RuntimeError("c")])
    with pytest.raises(RuntimeError, match="judge"):
        call(LangChainLLM(chat, max_retries=2))
    assert chat.runnable.calls == 3


def test_adapter_rejects_invalid_schema_output():
    chat = StubChat([{"status": "peut-être"}] * 2)
    with pytest.raises(RuntimeError):
        call(LangChainLLM(chat, max_retries=1))


def test_provider_factory():
    assert isinstance(get_llm(Settings(llm_provider="fake")), RuleBasedLLM)
    with pytest.raises(ValueError):
        get_chat_model(Settings(llm_provider="inconnu"))
    assert get_embedder(Settings(embeddings_provider="none")) is None
    with pytest.raises(ValueError):
        get_embedder(Settings(embeddings_provider="inconnu"))


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "Azure")
    monkeypatch.setenv("TOP_K", "6")
    s = Settings.from_env()
    assert s.llm_provider == "azure" and s.top_k == 6


def test_adapter_does_not_retry_auth_errors():
    class AuthenticationError(Exception):  # même nom que l'erreur du SDK OpenAI
        pass

    chat = StubChat([AuthenticationError("clé invalide"), {"status": "absent"}])
    with pytest.raises(AuthenticationError):
        call(LangChainLLM(chat, max_retries=2))
    assert chat.runnable.calls == 1


def test_azure_requires_its_env_vars(monkeypatch):
    pytest.importorskip("langchain_openai")
    for name in ("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT"):
        monkeypatch.delenv(name, raising=False)
    with pytest.raises(ValueError, match="AZURE_OPENAI_ENDPOINT"):
        get_chat_model(Settings(llm_provider="azure"))


def test_adapter_does_not_multiply_retries_already_done_by_the_sdk():
    class RateLimitError(Exception):  # déjà réessayée avec attente par le client OpenAI
        pass

    chat = StubChat([RateLimitError("429"), {"status": "absent"}])
    with pytest.raises(RateLimitError):
        call(LangChainLLM(chat, max_retries=2))
    assert chat.runnable.calls == 1
