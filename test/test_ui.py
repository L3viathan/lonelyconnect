import yaml

import freezegun

from lonelyconnect import game


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
    assert requests.get(
        "/ui/admin", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    assert not requests.get(
        "/ui/admin", headers={"Authorization": f"Bearer {player_token}"}
    ).ok


def test_ui_buzzer(requests, admin_token, player_token):
    assert not requests.get(
        "/ui/buzzer", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    game.GAME.buzz_state = "inactive"
    r = requests.get("/ui/buzzer", headers={"Authorization": f"Bearer {player_token}"})
    assert r.text.count("disabled") == 2

    game.GAME.buzz_state = "active"
    r = requests.get("/ui/buzzer", headers={"Authorization": f"Bearer {player_token}"})
    assert r.text.count("disabled") == 1


def test_ui_stage(requests, sample_game):
    game.GAME = sample_game
    game.GAME.points["left"] = 23

    r = requests.get("/ui/stage")
    assert "23" in r.text

    game.GAME.action("next")
    game.GAME.action("next")
    r = requests.get("/ui/stage")
    assert "<br>" in r.text


def test_ui_end2end(requests, admin_token, player_token):
    game.GAME = game.Game()
    with open("tutorial.yml") as f:
        game.GAME.load(yaml.load(f, Loader=yaml.SafeLoader))

    # Connections
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    assert requests.post(
        f"/action/start_right", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/buzz", headers={"Authorization": f"Bearer {player_token}"}
    ).ok
    assert requests.post(
        f"/action/no_points", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    assert requests.post(
        f"/action/start_left", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert not requests.post(
        f"/buzz", headers={"Authorization": f"Bearer {player_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/award_bonus", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    # Sequences
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    assert requests.post(
        f"/action/start_right", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert "questionmark" in requests.get(f"/ui/stage").text
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/award_bonus", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    assert requests.post(
        f"/action/start_left", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert "questionmark" in requests.get(f"/ui/stage").text
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/award_bonus", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok
    assert requests.post(
        f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
    ).ok

    # Missing Vowels
    with freezegun.freeze_time() as t:
        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok

        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
        # now we see the answer
        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
        # now we see the first clue
        stage = requests.get("/ui/stage").text
        answer = game.GAME.part.task.phrase.answer
        assert game.obfuscate(answer).replace(" ", "") in stage.replace(" ", "")
        assert (
            answer
            in requests.get(
                "/ui/admin", headers={"Authorization": f"Bearer {admin_token}"}
            ).text
        )
        assert requests.post(
            f"/buzz", headers={"Authorization": f"Bearer {player_token}"}
        ).ok
        assert requests.post(
            f"/action/punish_primary",
            headers={"Authorization": f"Bearer {admin_token}"},
        ).ok
        assert requests.post(
            f"/action/fake", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
        while game.GAME.part.tasks and "next" in game.GAME.actions():
            assert requests.post(
                f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
            ).ok
        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
        t.tick(999)
        assert requests.post(
            f"/action/next", headers={"Authorization": f"Bearer {admin_token}"}
        ).ok
