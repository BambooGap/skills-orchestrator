"""GitHub pull request comment upsert helper for automation.

The CLI core does not call this module. It is an integration boundary used by
the composite GitHub Action and by tests with a fake transport.
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from skills_orchestrator.github_pr import REGISTRY_DIFF_COMMENT_MARKER

UrlOpen = Callable[[urllib.request.Request], Any]


@dataclass(frozen=True)
class CommentUpsertResult:
    """Result of creating, updating, or reusing a PR comment."""

    action: str
    html_url: str | None


class GitHubCommentError(RuntimeError):
    """Raised when GitHub comment automation cannot complete."""


def upsert_marker_comment(
    *,
    api_url: str,
    token: str,
    repository: str,
    issue_number: int,
    body: str,
    marker: str = REGISTRY_DIFF_COMMENT_MARKER,
    allowed_author_logins: tuple[str, ...] = ("github-actions[bot]",),
    urlopen: UrlOpen = urllib.request.urlopen,
) -> CommentUpsertResult:
    """Create or update the latest issue comment containing marker."""
    if not token:
        raise GitHubCommentError("GitHub token is required")
    if marker not in body:
        raise GitHubCommentError("Comment body does not contain the expected marker")

    client = _IssueCommentClient(api_url=api_url, token=token, urlopen=urlopen)
    comments = client.list_comments(repository=repository, issue_number=issue_number)
    matching = [
        comment
        for comment in comments
        if marker in str(comment.get("body", ""))
        and _comment_author_allowed(comment, allowed_author_logins)
    ]
    existing = matching[-1] if matching else None
    if existing and existing.get("body") == body:
        return CommentUpsertResult(action="noop", html_url=existing.get("html_url"))
    if existing:
        updated = client.update_comment(str(existing["url"]), body=body)
        return CommentUpsertResult(action="updated", html_url=updated.get("html_url"))
    created = client.create_comment(repository=repository, issue_number=issue_number, body=body)
    return CommentUpsertResult(action="created", html_url=created.get("html_url"))


def upsert_from_github_event(
    *,
    body_file: str | Path,
    token: str,
    event_path: str | Path,
    api_url: str,
    allowed_author_logins: tuple[str, ...] = ("github-actions[bot]",),
    urlopen: UrlOpen = urllib.request.urlopen,
) -> CommentUpsertResult:
    """Read GitHub Actions event JSON and upsert a PR comment."""
    event = json.loads(Path(event_path).read_text(encoding="utf-8"))
    pull_request = event.get("pull_request")
    if not pull_request:
        return CommentUpsertResult(action="skipped", html_url=None)
    return upsert_marker_comment(
        api_url=api_url,
        token=token,
        repository=event["repository"]["full_name"],
        issue_number=int(pull_request["number"]),
        body=Path(body_file).read_text(encoding="utf-8"),
        allowed_author_logins=allowed_author_logins,
        urlopen=urlopen,
    )


class _IssueCommentClient:
    def __init__(self, *, api_url: str, token: str, urlopen: UrlOpen):
        self.api_url = api_url.rstrip("/")
        self.urlopen = urlopen
        self.headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "skills-orchestrator-action",
        }

    def list_comments(self, *, repository: str, issue_number: int) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        page = 1
        while True:
            repo = urllib.parse.quote(repository, safe="/")
            url = f"{self.api_url}/repos/{repo}/issues/{issue_number}/comments?per_page=100&page={page}"
            batch = self._request("GET", url) or []
            comments.extend(batch)
            if len(batch) < 100:
                return comments
            page += 1

    def create_comment(self, *, repository: str, issue_number: int, body: str) -> dict[str, Any]:
        repo = urllib.parse.quote(repository, safe="/")
        url = f"{self.api_url}/repos/{repo}/issues/{issue_number}/comments"
        return self._request("POST", url, {"body": body}) or {}

    def update_comment(self, url: str, *, body: str) -> dict[str, Any]:
        return self._request("PATCH", url, {"body": body}) or {}

    def _request(
        self,
        method: str,
        url: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=self.headers, method=method)
        try:
            with self.urlopen(request, timeout=30) as response:
                raw = response.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise GitHubCommentError(
                f"GitHub API {method} {url} failed: {exc.code} {detail}"
            ) from exc


def _comment_author_allowed(comment: dict[str, Any], allowed_logins: tuple[str, ...]) -> bool:
    user = comment.get("user") or {}
    login = str(user.get("login", ""))
    user_type = str(user.get("type", ""))
    return login in allowed_logins and user_type.lower() == "bot"


def _allowed_author_logins_from_env() -> tuple[str, ...]:
    raw = os.environ.get("SKILLS_ORCHESTRATOR_COMMENT_AUTHOR_LOGINS", "github-actions[bot]")
    logins = tuple(login.strip() for login in raw.split(",") if login.strip())
    return logins or ("github-actions[bot]",)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint used by the composite GitHub Action."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--body-file", required=True)
    args = parser.parse_args(argv)

    result = upsert_from_github_event(
        body_file=args.body_file,
        token=os.environ.get("GITHUB_TOKEN", ""),
        event_path=os.environ.get("GITHUB_EVENT_PATH", ""),
        api_url=os.environ.get("GITHUB_API_URL", "https://api.github.com"),
        allowed_author_logins=_allowed_author_logins_from_env(),
    )
    if result.html_url:
        print(f"{result.action}: {result.html_url}")
    else:
        print(result.action)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
