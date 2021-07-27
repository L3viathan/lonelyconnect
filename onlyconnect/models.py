from enum import Enum
from collections import Counter
from typing import Literal, Optional
from pydantic import BaseModel

class BuzzState(Enum):
    inactive = "inactive"
    active = "active"
    active_left = "active-left"
    active_right = "active-right"
    left = "left"
    right = "right"


class User(BaseModel):
    name: Literal["left", "right", "admin"]
    descriptive_name: Optional[str]

    @property
    def is_admin(self):
        return self.name == "admin"

    @property
    def is_player(self):
        return self.name in ("left", "right")

    def get_token(self, tokens):
        for token in tokens:
            if tokens[token] == self.name:
                return token
        raise RuntimeError(f"Couldn't find token for user {self.name}")



class State(BaseModel):
    """
    Contains all PUBLIC information about the current game state.
    """
    points: dict = {"left": 0, "right": 0}
    buzz: BuzzState = "inactive"
    stage: Literal["connections", "sequences", "wall", "missing vowels"] = "connections"
