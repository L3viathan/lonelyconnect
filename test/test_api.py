import pytest

from lonelyconnect import game


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
