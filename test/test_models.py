import pytest

import lonelyconnect


def test_normal_user():
    user = lonelyconnect.models.User(name="left")
    assert not user.is_admin
    assert user.is_player


def test_normal_user():
    user = lonelyconnect.models.User(name="admin")
    assert user.is_admin
    assert not user.is_player


def test_get_token():
    user = lonelyconnect.models.User(name="left")
    assert user.get_token({"foo": "left", "bar": "admin"}) == "foo"
    with pytest.raises(RuntimeError):
        user.get_token({})
