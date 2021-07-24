from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # camel case because OpenAPI
TOKENS = {}
USERS = {}


def logged_in(token: str = Depends(oauth2_scheme)):
    return USERS[TOKENS[token]]

def player(token: str = Depends(oauth2_scheme)):
    user = logged_in(token)
    if not user.is_player:
        raise HTTPException(
            status_code=401,
            detail="Only accessible to players",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def admin(token: str = Depends(oauth2_scheme)):
    user = logged_in(token)
    if not user.is_admin:
        raise HTTPException(
            status_code=401,
            detail="Only accessible to admins",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
