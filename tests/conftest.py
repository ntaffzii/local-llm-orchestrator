import pytest

import services.orchestrator.main as main_module


@pytest.fixture(autouse=True)
def _reset_auth_throttle():
    # The auth throttle and per-key rate limiter are process-global state; isolate them
    # so counts from one test cannot affect later tests that share the TestClient IP.
    main_module.auth_throttle.reset()
    main_module.rate_limiter.reset()
    yield
    main_module.auth_throttle.reset()
    main_module.rate_limiter.reset()
