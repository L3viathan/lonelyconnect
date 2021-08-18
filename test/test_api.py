import asyncio

import pytest
from fastapi.testclient import TestClient

from lonelyconnect import app, auth, startup, game, shutdown


@pytest.fixture(scope="session")
def requests():
    client = TestClient(app)
    asyncio.run(startup())
    yield client
    asyncio.run(shutdown())


@pytest.fixture(scope="session")
def admin_token(requests):
    admin = auth.USERS["admin"]
    code = admin.get_token(auth.CODES)
    r = requests.post(
        "/login",
        data={"grant_type": "password", "username": "nobody", "password": "wrong"},
        headers={"HX-Request": "true"},
    )
    assert not r.ok
    r = requests.post(
        "/login",
        data={"grant_type": "password", "username": "nobody", "password": code},
        headers={"HX-Request": "true"},
    )
    assert r.ok
    yield r.json()["access_token"]


@pytest.fixture(scope="session")
def player_token(requests, admin_token):
    r = requests.post("/pair/right", headers={"Authorization": f"Bearer {admin_token}"})
    code = r.json()
    r = requests.post(
        "/login",
        data={"grant_type": "password", "username": "nobody", "password": code},
        headers={"HX-Request": "true"},
    )
    assert r.ok
    yield r.json()["access_token"]


def test_auth(requests, admin_token):
    r = requests.get("/codes", headers={"Authorization": f"Bearer wrong"})
    assert not r.ok

    r = requests.get("/codes", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.ok
    assert r.json() == {}

    r = requests.post("/pair/left", headers={"Authorization": f"Bearer {admin_token}"})
    left_code = r.json()

    r = requests.post("/pair/right", headers={"Authorization": f"Bearer {admin_token}"})
    right_code = r.json()

    r = requests.get("/codes", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.json() == {left_code: "left", right_code: "right"}


def test_roles(requests, admin_token, player_token):
    assert requests.get("/codes", headers={"Authorization": f"Bearer {admin_token}"}).ok
    assert not requests.get(
        "/codes", headers={"Authorization": f"Bearer {player_token}"}
    ).ok

    game.GAME.buzz_state = "active"
    assert not requests.post(
        "/buzz", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        "/buzz", headers={"Authorization": f"Bearer {player_token}"}
    ).ok


def test_ui_redirect(requests, admin_token, player_token):
    r = requests.post("/ui/redirect", data={"access_token": admin_token})
    assert "/ui/admin" in r.text
    assert "/ui/buzzer" not in r.text

    r = requests.post("/ui/redirect", data={"access_token": player_token})
    assert "/ui/admin" not in r.text
    assert "/ui/buzzer" in r.text


def test_ui_login(requests):
    assert requests.get("/ui/login").ok


def test_ui_admin(requests, admin_token, player_token):
    assert requests.get("/ui/admin", headers={"Authorization": f"Bearer {admin_token}"}).ok

    assert not requests.get("/ui/admin", headers={"Authorization": f"Bearer {player_token}"}).ok
