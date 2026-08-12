from __future__ import annotations

import server.idc_server as web


def test_query_token_is_not_accepted_or_redirected(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "secret-token")
    web.app.config.update(TESTING=True)
    client = web.app.test_client()
    response = client.get("/?token=secret-token")
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")
    assert "secret-token" not in response.headers["Location"]


def test_login_uses_session_and_post_requires_csrf(monkeypatch):
    monkeypatch.setattr(web, "ACCESS_TOKEN", "secret-token")
    web.app.config.update(TESTING=True)
    client = web.app.test_client()
    login = client.post("/login", data={"access_token": "secret-token"})
    assert login.status_code == 302
    assert "secret-token" not in login.headers["Location"]
    forbidden = client.post("/jobs", data={})
    assert forbidden.status_code == 403
