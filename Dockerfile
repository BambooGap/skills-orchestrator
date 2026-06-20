FROM python:3.12-slim

LABEL org.opencontainers.image.title="skills-orchestrator" \
      org.opencontainers.image.description="SkillOps CLI for agent instruction governance" \
      org.opencontainers.image.source="https://github.com/BambooGap/skills-orchestrator"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md LICENSE constraints.txt ./
COPY skills_orchestrator ./skills_orchestrator

RUN python -m pip install -c constraints.txt . \
    && adduser --disabled-password --gecos "" --uid 10001 appuser

USER appuser

ENTRYPOINT ["skills-orchestrator"]
CMD ["--help"]
