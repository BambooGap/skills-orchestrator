# python:3.12.13-slim-trixie manifest-list digest, refreshed during reviewed release hygiene.
FROM python:3.12-slim@sha256:6c4dd321d176d61ea848dc8c73a4f7dbae8f70e0ee48bb411ea2f045b599fa8e

LABEL org.opencontainers.image.title="skills-orchestrator" \
      org.opencontainers.image.description="SkillOps CLI for agent instruction governance" \
      org.opencontainers.image.source="https://github.com/BambooGap/skills-orchestrator"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

COPY pyproject.toml README.md LICENSE constraints.txt ./
COPY skills_orchestrator ./skills_orchestrator

RUN python -m pip install -c constraints.txt . \
    && adduser --disabled-password --gecos "" --uid 10001 appuser

USER appuser

ENTRYPOINT ["skills-orchestrator"]
CMD ["--help"]
