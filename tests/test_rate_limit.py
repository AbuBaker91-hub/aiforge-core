from fastapi.testclient import TestClient

from aiforge_core.app import create_app


def test_31st_request_in_a_minute_gets_429():
    app = create_app(rate_limit_per_min=30)

    @app.get("/ping")
    def ping():
        return {"pong": True}

    client = TestClient(app)
    statuses = [client.get("/ping").status_code for _ in range(31)]
    assert statuses[:30] == [200] * 30
    assert statuses[30] == 429


def test_health_is_exempt_and_green():
    app = create_app(rate_limit_per_min=1)
    client = TestClient(app)
    for _ in range(5):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"ok": True}
