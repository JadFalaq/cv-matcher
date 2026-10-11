"""Couche d'accès au LLM (et aux embeddings) : une seule interface, plusieurs fournisseurs."""

from __future__ import annotations

import logging
import os
from typing import Any, Protocol, Sequence, TypeVar

from pydantic import BaseModel

from .config import Settings

T = TypeVar("T", bound=BaseModel)
log = logging.getLogger("cvmatch.llm")


class LLM(Protocol):
    """Interface minimale : une sortie structurée (schéma Pydantic) à partir d'un prompt.

    `tag` identifie le nœud appelant ; `context` est ignoré par les vrais LLM et sert uniquement au
    LLM factice (tests / démo hors ligne).
    """

    def structured(
        self, schema: type[T], *, system: str, user: str, tag: str, context: dict[str, Any] | None = None
    ) -> T: ...


# Erreurs du SDK OpenAI qu'un nouvel essai ne corrigera pas (clé, droits, déploiement, requête invalide).
FATAL_ERRORS = {"AuthenticationError", "PermissionDeniedError", "NotFoundError", "BadRequestError"}
# Erreurs déjà réessayées avec attente par le client du fournisseur (429, délai, réseau, 5xx) :
# les réessayer ici multiplierait les attentes (une analyse semblait alors tourner sans fin).
_ALREADY_RETRIED = {"RateLimitError", "APITimeoutError", "APIConnectionError", "InternalServerError"}


class LangChainLLM:
    """Adaptateur autour d'un chat model LangChain avec `with_structured_output`.

    Les erreurs réseau et 429 sont déjà réessayées (avec attente) par le client du fournisseur ;
    la boucle ici rattrape surtout les sorties structurées invalides.
    """

    def __init__(self, chat_model: Any, max_retries: int = 2):
        self._chat = chat_model
        self.max_retries = max_retries

    def structured(
        self, schema: type[T], *, system: str, user: str, tag: str, context: dict[str, Any] | None = None
    ) -> T:
        runnable = self._chat.with_structured_output(schema)
        messages = [("system", system), ("human", user)]
        last: Exception | None = None
        for attempt in range(1, self.max_retries + 2):
            try:
                out = runnable.invoke(messages)
                return out if isinstance(out, schema) else schema.model_validate(out)
            except Exception as exc:  # sortie invalide, erreur transitoire…
                name = type(exc).__name__
                if name in FATAL_ERRORS or name in _ALREADY_RETRIED:
                    log.error("Appel LLM '%s' en échec : %s", tag, name)
                    raise
                log.warning("Appel LLM '%s' : %s (essai %d/%d)", tag, name, attempt, self.max_retries + 1)
                last = exc
        raise RuntimeError(f"Échec de la sortie structurée pour '{tag}' après {self.max_retries + 1} essais") from last


def _temperature(settings: Settings) -> dict[str, float]:
    if settings.llm_temperature in ("none", "null", ""):
        return {}
    return {"temperature": float(settings.llm_temperature)}


def _require_env(*names: str) -> None:
    missing = [n for n in names if not os.getenv(n)]
    if missing:
        raise ValueError(f"Variables d'environnement manquantes : {', '.join(missing)}")


def get_chat_model(settings: Settings) -> Any:
    p = settings.llm_provider
    temp = _temperature(settings)
    if p == "azure":
        from langchain_openai import AzureChatOpenAI

        _require_env("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_DEPLOYMENT")
        return AzureChatOpenAI(
            azure_deployment=os.environ["AZURE_OPENAI_DEPLOYMENT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
            timeout=settings.llm_timeout,
            max_retries=2,
            **temp,
        )
    if p == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=settings.llm_model or "gpt-4o-mini", timeout=settings.llm_timeout, max_retries=2, **temp)
    if p == "anthropic":
        from langchain_anthropic import ChatAnthropic

        if not settings.llm_model:
            raise ValueError("Définis LLM_MODEL pour le fournisseur anthropic.")
        return ChatAnthropic(model=settings.llm_model, **temp)
    if p == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(model=settings.llm_model or "llama3.1", **temp)
    raise ValueError(f"Fournisseur LLM inconnu : {p!r}")


def get_llm(settings: Settings) -> LLM:
    if settings.llm_provider == "fake":
        from .fake_llm import RuleBasedLLM

        return RuleBasedLLM()
    return LangChainLLM(get_chat_model(settings))


def get_embedder(settings: Settings):
    """Retourne une fonction `list[str] -> vecteurs`, ou None (recherche lexicale seule)."""
    p = settings.embeddings_provider
    if p in ("none", "", None):
        return None
    if p == "azure":
        from langchain_openai import AzureOpenAIEmbeddings

        _require_env("AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY", "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT")
        emb = AzureOpenAIEmbeddings(
            azure_deployment=os.environ["AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT"],
            api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21"),
        )
    elif p == "openai":
        from langchain_openai import OpenAIEmbeddings

        emb = OpenAIEmbeddings(model=settings.embeddings_model or "text-embedding-3-small")
    elif p == "ollama":
        from langchain_ollama import OllamaEmbeddings

        emb = OllamaEmbeddings(model=settings.embeddings_model or "nomic-embed-text")
    else:
        raise ValueError(f"Fournisseur d'embeddings inconnu : {p!r}")

    def embed(texts: Sequence[str]):
        return emb.embed_documents(list(texts))

    return embed
