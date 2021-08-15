from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from .models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # camel case because OpenAPI
TOKENS = {}
USERS = {
    "admin": User(name="admin"),
    "left": User(name="left"),
    "right": User(name="right"),
}
CODES = {}


def logged_in(token: str = Depends(oauth2_scheme)):
    try:
        return USERS[TOKENS[token]]
    except KeyError:
        raise HTTPException(
            status_code=401,
            detail="Only accessible to logged in users",
            headers={"WWW-Authenticate": "Bearer"},
        )

def player(token: str = Depends(oauth2_scheme)):
    user = logged_in(token)
    if not user.is_player:
        raise HTTPException(
            status_code=403,
            detail="Only accessible to players",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def admin(token: str = Depends(oauth2_scheme)):
    user = logged_in(token)
    if not user.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only accessible to admins",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
