import asyncio
import textwrap

import pytest
import yaml
from fastapi.testclient import TestClient

from lonelyconnect import app, auth, game, startup, shutdown


@pytest.fixture
def sample_game():
    g = game.Game()
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
