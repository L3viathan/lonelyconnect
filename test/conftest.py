import textwrap

import pytest
import yaml

import lonelyconnect


@pytest.fixture
def sample_game():
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
