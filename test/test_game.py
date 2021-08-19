from unittest.mock import MagicMock

import freezegun
import pytest


@pytest.mark.parametrize(
    ("initial_state", "buzzer", "success"),
    [
        ("inactive", "left", False),
        ("active", "left", True),
        ("active-left", "left", True),
        ("active-right", "left", False),
        ("right", "left", False),
    ],
)
def test_buzz(sample_game, initial_state, buzzer, success):
    sample_game.buzz_state = initial_state
    if success:
        assert sample_game.buzz(buzzer) == buzzer
    else:
        with pytest.raises(PermissionError):
            sample_game.buzz(buzzer)


@pytest.mark.parametrize(
    "success",
    [
        True,
        False,
    ],
)
def test_buzz_propagates(sample_game, success):
    sample_game.part = MagicMock()
    sample_game.buzz_state = "active" if success else "inactive"
    try:
        sample_game.buzz("right")
    except:
        pass
    if success:
        sample_game.part.buzz.assert_called_with("right")
    else:
        sample_game.part.buzz.assert_not_called()


def test_connections(sample_game):
    sample_game.action("next")  # load part
    sample_game.action("next")  # load question
    sample_game.action("start_left")
    with pytest.raises(PermissionError):
        sample_game.buzz("right")
    sample_game.action("next")  # show one more clue
    sample_game.buzz("left")
    sample_game.action("award_primary")  # correct!
    assert sample_game.points == {"left": 3, "right": 0}

    sample_game.action("next")  # load question
    sample_game.action("start_right")
    sample_game.buzz("right")
    # right answers incorrectly
    sample_game.action("award_bonus")
    assert sample_game.points == {"left": 4, "right": 0}

    sample_game.action("next")  # load question
    with freezegun.freeze_time() as time:
        sample_game.action("start_left")
        time.tick(30.1)  # time expires
        with pytest.raises(PermissionError):
            sample_game.buzz("left")
        assert "award_bonus" in dict(sample_game.actions())
        sample_game.action("award_bonus")
    assert sample_game.points == {"left": 4, "right": 1}
    assert "next" in set(dict(sample_game.actions()))
    sample_game.action("next")  # next question (none left)
    sample_game.action("next")  # next part (none left)
    assert "next" not in set(dict(sample_game.actions()))
    assert sample_game.action("next") is None


def test_stage_and_secrets_and_actions(sample_game):
    assert sample_game.stage() == {"bigscores": True}
    assert sample_game.secrets() == {}
    assert set(dict(sample_game.actions())) == {"next"}
    sample_game.action("next")  # load part
    assert sample_game.stage() == {"bigscores": True}
    assert sample_game.secrets() == {}
    assert set(dict(sample_game.actions())) == {"next"}
    sample_game.action("next")  # load question
    assert sample_game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [],
        "time_remaining": None,
        "time_total": None,
    }
    assert sample_game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": [],
    }
    assert set(dict(sample_game.actions())) == {"start_left", "start_right"}
    sample_game.action("start_left")
    assert sample_game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [{"label": "Hint 1", "type": "text"}],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert sample_game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1"],
    }
    assert set(dict(sample_game.actions())) == {"next"}
    sample_game.action("next")  # show one more clue
    assert sample_game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [
            {"label": "Hint 1", "type": "text"},
            {"label": "Hint 2", "type": "text"},
        ],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert sample_game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1", "Explanation 2"],
    }
    assert set(dict(sample_game.actions())) == {"next"}
    sample_game.buzz("left")
    assert sample_game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [
            {"label": "Hint 1", "type": "text"},
            {"label": "Hint 2", "type": "text"},
        ],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert sample_game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1", "Explanation 2"],
    }
    assert set(dict(sample_game.actions())) == {
        "next",
        "award_bonus",
        "award_primary",
        "no_points",
    }


def test_buzz_timer(sample_game):
    sample_game.action("next")  # load part
    sample_game.action("next")  # load question
    sample_game.action("start_left")
    assert sample_game.buzz_state == "active-left"
    with freezegun.freeze_time() as time:
        time.tick(30.1)  # time expires
        sample_game.stage()
    assert sample_game.buzz_state == "inactive"
