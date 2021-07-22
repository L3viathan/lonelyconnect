from typing import Literal, Optional
from pydantic import BaseModel

class User(BaseModel):
    name: Literal["left", "right", "admin"]
    descriptive_name: Optional[str]
    score: int = 0

    @property
    def is_admin(self):
        return self.name == "admin"

    @property
    def is_player(self):
        return self.name in ("left", "right")


class State(BaseModel):
    """
    Contains all PUBLIC information about the current game state.
    """
    left: Optional[User]
    right: Optional[User]
    buzz: Literal["inactive", "active", "left", "right"] = "inactive"
    stage: Literal["connections", "sequences", "wall", "missing vowels"] = "connections"
