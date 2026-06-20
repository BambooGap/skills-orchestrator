import json
from pathlib import Path

from skills_orchestrator.github_pr import REGISTRY_DIFF_COMMENT_MARKER
from skills_orchestrator.integrations.github_pr_comment import (
    upsert_from_github_event,
    upsert_marker_comment,
)


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class _FakeGitHub:
    def __init__(self, comments):
        self.comments = list(comments)
        self.requests = []

    def __call__(self, request, timeout=30):
        payload = None
        if request.data:
            payload = json.loads(request.data.decode("utf-8"))
        self.requests.append((request.get_method(), request.full_url, payload, timeout))

        method = request.get_method()
        if method == "GET":
            return _Response(self.comments)
        if method == "POST":
            created = {
                "url": "https://api.github.test/repos/org/repo/issues/comments/1",
                "html_url": "https://github.test/org/repo/pull/1#issuecomment-1",
                "body": payload["body"],
            }
            self.comments.append(created)
            return _Response(created)
        if method == "PATCH":
            updated = {
                "url": request.full_url,
                "html_url": "https://github.test/org/repo/pull/1#issuecomment-1",
                "body": payload["body"],
            }
            return _Response(updated)
        raise AssertionError(f"unexpected method: {method}")


def test_upsert_marker_comment_creates_when_missing():
    fake = _FakeGitHub([])
    body = f"{REGISTRY_DIFF_COMMENT_MARKER}\n# Registry Diff\n"

    result = upsert_marker_comment(
        api_url="https://api.github.test",
        token="token",
        repository="org/repo",
        issue_number=1,
        body=body,
        urlopen=fake,
    )

    assert result.action == "created"
    assert [request[0] for request in fake.requests] == ["GET", "POST"]


def test_upsert_marker_comment_updates_existing_marker():
    fake = _FakeGitHub(
        [
            {
                "url": "https://api.github.test/repos/org/repo/issues/comments/1",
                "html_url": "https://github.test/org/repo/pull/1#issuecomment-1",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
                "body": f"{REGISTRY_DIFF_COMMENT_MARKER}\nold",
            }
        ]
    )
    body = f"{REGISTRY_DIFF_COMMENT_MARKER}\nnew"

    result = upsert_marker_comment(
        api_url="https://api.github.test",
        token="token",
        repository="org/repo",
        issue_number=1,
        body=body,
        urlopen=fake,
    )

    assert result.action == "updated"
    assert [request[0] for request in fake.requests] == ["GET", "PATCH"]


def test_upsert_marker_comment_noops_when_body_matches():
    body = f"{REGISTRY_DIFF_COMMENT_MARKER}\nunchanged"
    fake = _FakeGitHub(
        [
            {
                "url": "https://api.github.test/repos/org/repo/issues/comments/1",
                "html_url": "https://github.test/org/repo/pull/1#issuecomment-1",
                "user": {"login": "github-actions[bot]", "type": "Bot"},
                "body": body,
            }
        ]
    )

    result = upsert_marker_comment(
        api_url="https://api.github.test",
        token="token",
        repository="org/repo",
        issue_number=1,
        body=body,
        urlopen=fake,
    )

    assert result.action == "noop"
    assert [request[0] for request in fake.requests] == ["GET"]


def test_upsert_marker_comment_ignores_foreign_marker_comments():
    fake = _FakeGitHub(
        [
            {
                "url": "https://api.github.test/repos/org/repo/issues/comments/1",
                "html_url": "https://github.test/org/repo/pull/1#issuecomment-1",
                "user": {"login": "contributor", "type": "User"},
                "body": f"{REGISTRY_DIFF_COMMENT_MARKER}\nold",
            }
        ]
    )
    body = f"{REGISTRY_DIFF_COMMENT_MARKER}\naction owned"

    result = upsert_marker_comment(
        api_url="https://api.github.test",
        token="token",
        repository="org/repo",
        issue_number=1,
        body=body,
        urlopen=fake,
    )

    assert result.action == "created"
    assert [request[0] for request in fake.requests] == ["GET", "POST"]


def test_upsert_from_event_skips_non_pr_payload(tmp_path):
    event = tmp_path / "event.json"
    event.write_text('{"repository":{"full_name":"org/repo"}}', encoding="utf-8")
    body = tmp_path / "body.md"
    body.write_text(f"{REGISTRY_DIFF_COMMENT_MARKER}\nbody", encoding="utf-8")

    result = upsert_from_github_event(
        body_file=body,
        token="token",
        event_path=event,
        api_url="https://api.github.test",
        urlopen=_FakeGitHub([]),
    )

    assert result.action == "skipped"
    assert result.html_url is None


def test_upsert_from_event_reads_repository_and_pr_number(tmp_path):
    event = tmp_path / "event.json"
    event.write_text(
        json.dumps({"repository": {"full_name": "org/repo"}, "pull_request": {"number": 7}}),
        encoding="utf-8",
    )
    body = Path(tmp_path / "body.md")
    body.write_text(f"{REGISTRY_DIFF_COMMENT_MARKER}\nbody", encoding="utf-8")
    fake = _FakeGitHub([])

    result = upsert_from_github_event(
        body_file=body,
        token="token",
        event_path=event,
        api_url="https://api.github.test",
        urlopen=fake,
    )

    assert result.action == "created"
    assert "/repos/org/repo/issues/7/comments" in fake.requests[0][1]
