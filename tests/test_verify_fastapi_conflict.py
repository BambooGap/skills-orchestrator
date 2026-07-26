from scripts.verify_fastapi_conflict import (
    is_fastapi_starlette_conflict,
    verify_rejection,
)


def test_install_dependency_conflict_is_accepted():
    ok, _ = verify_rejection(
        install_status=1,
        install_log=(
            "ERROR: Cannot install fastapi==0.116.1 because it requires "
            "starlette<0.48 and sse-starlette requires starlette>=0.49.1."
        ),
    )

    assert ok is True


def test_network_failure_is_not_misclassified_as_dependency_conflict():
    ok, message = verify_rejection(
        install_status=1,
        install_log=(
            "WARNING: Retrying after connection broken by NewConnectionError. "
            "Could not reach https://pypi.org/simple/fastapi/"
        ),
    )

    assert ok is False
    assert "network" in message


def test_network_failure_wins_over_dependency_context_in_install_log():
    ok, message = verify_rejection(
        install_status=1,
        install_log=(
            "Collecting fastapi==0.116.1\n"
            "fastapi 0.116.1 requires starlette<0.48.0\n"
            "Retrying after NewConnectionError while fetching starlette\n"
            "ERROR: Could not reach pypi.org\n"
        ),
    )

    assert ok is False
    assert "network" in message


def test_install_failure_requires_explicit_resolver_terminal_marker():
    ok, message = verify_rejection(
        install_status=1,
        install_log=(
            "Collecting fastapi==0.116.1\n"
            "fastapi 0.116.1 requires starlette<0.48.0\n"
            "ERROR: subprocess exited unexpectedly\n"
        ),
    )

    assert ok is False
    assert "other than" in message


def test_successful_install_requires_matching_pip_check_failure():
    ok, _ = verify_rejection(
        install_status=0,
        install_log="installed",
        pip_check_status=1,
        pip_check_log=(
            "fastapi 0.116.1 has requirement starlette<0.48.0,>=0.40.0, "
            "but you have starlette 1.3.1."
        ),
    )

    assert ok is True


def test_pip_check_packages_on_unrelated_lines_are_rejected():
    ok, _ = verify_rejection(
        install_status=0,
        install_log="installed",
        pip_check_status=1,
        pip_check_log=(
            "package-a has requirement fastapi>=1, but you have fastapi 0.116.1.\n"
            "package-b has requirement starlette<0.48, but you have starlette 1.3.1.\n"
            "package-c has requirement numpy>=2.0, but you have numpy 1.0.\n"
        ),
    )

    assert ok is False


def test_expected_pip_check_conflict_plus_extra_conflict_is_rejected():
    ok, _ = verify_rejection(
        install_status=0,
        install_log="installed",
        pip_check_status=1,
        pip_check_log=(
            "fastapi 0.116.1 has requirement starlette<0.48.0,>=0.40.0, "
            "but you have starlette 1.3.1.\n"
            "package-c 1.0 has requirement numpy>=2.0, but you have numpy 1.0.\n"
        ),
    )

    assert ok is False


def test_unrelated_pip_check_failure_is_rejected():
    ok, _ = verify_rejection(
        install_status=0,
        install_log="installed",
        pip_check_status=1,
        pip_check_log="example-package requires missing-package",
    )

    assert ok is False


def test_conflict_match_requires_both_packages():
    assert is_fastapi_starlette_conflict("fastapi requires another-package") is False
