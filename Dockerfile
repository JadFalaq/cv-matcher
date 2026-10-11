# Image de l'API (FastAPI). Le site Next.js (web/) se déploie à part, par exemple sur Vercel.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000

# Utilisateur non-root (uid 1000 : requis par Hugging Face Spaces)
RUN useradd --create-home --uid 1000 app
WORKDIR /home/app/cvmatch

COPY --chown=app pyproject.toml README.md ./
COPY --chown=app src ./src
RUN pip install ".[openai,api]"

COPY --chown=app data/sample_cv.md data/sample_offer.txt ./data/

USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s \
    CMD python -c "import os, urllib.request; urllib.request.urlopen(f'http://localhost:{os.environ[\"PORT\"]}/health')"

# --proxy-headers : la vraie IP du visiteur (derrière le proxy de l'hébergeur) sert à la limite de débit
CMD ["sh", "-c", "uvicorn cvmatch.api:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
