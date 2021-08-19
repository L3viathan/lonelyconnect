import textwrap
from unittest.mock import MagicMock

import freezegun
import pytest
import yaml

import lonelyconnect


@pytest.fixture
def game():
    g = lonelyconnect.game.Game()
    g.load(
        yaml.load(
            textwrap.dedent(
                """
                parts:
                  - type: connections
                    questions:"""
                + textwrap.indent(
                    (
                        """
                    - answer: The answer
                      explanation: This would show extra info about the answer
                      steps:
                      - explanation: Explanation 1
                        label: Hint 1
                      - explanation: Explanation 2
                        label: Hint 2
                      - explanation: Explanation 3
                        label: Hint 3
                      - explanation: Explanation 4
                        label: Hint 4
                    """
                        * 3
                    ),
                    "    ",
                )
            ),
            Loader=yaml.SafeLoader,
        ),
    )
    yield g


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
def test_buzz(game, initial_state, buzzer, success):
    game.buzz_state = initial_state
    if success:
        assert game.buzz(buzzer) == buzzer
    else:
        with pytest.raises(PermissionError):
            game.buzz(buzzer)


@pytest.mark.parametrize(
    "success",
    [
        True,
        False,
    ],
)
def test_buzz_propagates(game, success):
    game.part = MagicMock()
    game.buzz_state = "active" if success else "inactive"
    try:
        game.buzz("right")
    except:
        pass
    if success:
        game.part.buzz.assert_called_with("right")
    else:
        game.part.buzz.assert_not_called()


def test_connections(game):
    game.action("next")  # load part
    game.action("next")  # load question
    game.action("start_left")
    with pytest.raises(PermissionError):
        game.buzz("right")
    game.action("next")  # show one more clue
    game.buzz("left")
    game.action("award_primary")  # correct!
    assert game.points == {"left": 3, "right": 0}

    game.action("next")  # load question
    game.action("start_right")
    game.buzz("right")
    # right answers incorrectly
    game.action("award_bonus")
    assert game.points == {"left": 4, "right": 0}

    game.action("next")  # load question
    with freezegun.freeze_time() as time:
        game.action("start_left")
        time.tick(30.1)  # time expires
        with pytest.raises(PermissionError):
            game.buzz("left")
        assert "award_bonus" in dict(game.actions())
        game.action("award_bonus")
    assert game.points == {"left": 4, "right": 1}
    assert "next" in set(dict(game.actions()))
    game.action("next")  # next question (none left)
    game.action("next")  # next part (none left)
    assert "next" not in set(dict(game.actions()))
    assert game.action("next") is None


def test_stage_and_secrets_and_actions(game):
    assert game.stage() == {"bigscores": True}
    assert game.secrets() == {}
    assert set(dict(game.actions())) == {"next"}
    game.action("next")  # load part
    assert game.stage() == {"bigscores": True}
    assert game.secrets() == {}
    assert set(dict(game.actions())) == {"next"}
    game.action("next")  # load question
    assert game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [],
        "time_remaining": None,
        "time_total": None,
    }
    assert game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": [],
    }
    assert set(dict(game.actions())) == {"start_left", "start_right"}
    game.action("start_left")
    assert game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [{"label": "Hint 1", "type": "text"}],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1"],
    }
    assert set(dict(game.actions())) == {"next"}
    game.action("next")  # show one more clue
    assert game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [
            {"label": "Hint 1", "type": "text"},
            {"label": "Hint 2", "type": "text"},
        ],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1", "Explanation 2"],
    }
    assert set(dict(game.actions())) == {"next"}
    game.buzz("left")
    assert game.stage() == {
        "answer": None,
        "clear": False,
        "steps": [
            {"label": "Hint 1", "type": "text"},
            {"label": "Hint 2", "type": "text"},
        ],
        "time_remaining": 29,
        "time_total": 30,
    }
    assert game.secrets() == {
        "explanation": "This would show extra info about the answer",
        "step_explanations": ["Explanation 1", "Explanation 2"],
    }
    assert set(dict(game.actions())) == {
        "next",
        "award_bonus",
        "award_primary",
        "no_points",
    }


def test_buzz_timer(game):
    game.action("next")  # load part
    game.action("next")  # load question
    game.action("start_left")
    assert game.buzz_state == "active-left"
    with freezegun.freeze_time() as time:
        time.tick(30.1)  # time expires
        game.stage()
    assert game.buzz_state == "inactive"
