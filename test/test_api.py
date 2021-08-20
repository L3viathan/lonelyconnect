import os
import asyncio
from pathlib import Path
from contextlib import contextmanager

import pytest

from lonelyconnect import game, startup, shutdown, auth


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


@contextmanager
def hide_true_swap_file():
    swap_path = Path("swap.bin")
    if swap_path.exists():
        hidden_path = swap_path.rename(".pytest-running.swap.bin")
    else:
        hidden_path = None
    try:
        yield
    finally:
        if hidden_path:
            hidden_path.rename(swap_path)


def test_swap_file(sample_game):
    original = os.environ.pop("lonelyconnect_no_swap")
    os.environ["lonelyconnect_admin_code"] = "123456"
    with hide_true_swap_file():
        asyncio.run(startup())
        game.GAME = sample_game
        game.GAME.arbitrary = "foobar"
        asyncio.run(shutdown())
        game.GAME.arbitrary = "barfoo"
        asyncio.run(startup())
    assert game.GAME.arbitrary == "foobar"
    del game.GAME.arbitrary
    if original:
        os.environ["lonelyconnect_no_swap"] = original


def test_various_admin_functions(requests, admin_token, sample_game):
    game.GAME = sample_game
    assert game.GAME.buzz_state == "inactive"
    requests.put("/buzz/active", headers={"Authorization": f"Bearer {admin_token}"})
    assert game.GAME.buzz_state == "active"

    requests.post(
        "/score/left",
        data={"points": 23},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert game.GAME.points["left"] == 23

    assert not auth.USERS["right"].descriptive_name
    requests.post(
        "/name/right",
        data={"teamname": "foobar"},
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert auth.USERS["right"].descriptive_name == "FOOBAR"
