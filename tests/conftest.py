import pytest

import services.orchestrator.main as main_module


@pytest.fixture(autouse=True)
def _reset_auth_throttle():
    # The auth throttle is process-global state; isolate it so failed-auth counts
    # from one test cannot lock out later tests that share the TestClient IP.
    main_module.auth_throttle.reset()
    yield
    main_module.auth_throttle.reset()
