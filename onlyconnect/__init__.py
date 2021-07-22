import random
from asyncio import Lock

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates

from .models import State, User

CODES = {}
TOKENS = {}
BUZZLOCK = Lock()
STATE = State()

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")  # camel case because OpenAPI
templates = Jinja2Templates(directory="templates")


def user_from_token(token: str = Depends(oauth2_scheme)):
    return TOKENS.get(token)


@app.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    # to implement in client:
    # HTTP POST request to /login with the following form-encoded fields:
    # - grant_type == "password"
    # - username = "anything, since we ignore it" (but probably non-empty)
    # - password = "ABC123" (our token)
    # the response is JSON, containing the `access_token` and the `token_type` ("bearer").

    # username is actually ignored. These are random single-use non-critical codes.
    username = CODES.pop(form_data.password, None)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = random_token(32)
    user = User(name=username)
    TOKENS[token] = user
    if user.is_player:
        setattr(STATE, username, user)
    return {"access_token": token, "token_type": "bearer"}


def random_token(length=6):
    return "".join(random.choices("ABCDEFGHKLMNPQRSTUVWXYZ23456789", k=length))


@app.on_event("startup")
async def startup():
    for username in ("admin", "left", "right"):
        code = random_token(6)
        if username == "admin":
            print("ADMIN CODE:", code)
        CODES[code] = username


@app.get("/codes")
async def codes(user: User = Depends(user_from_token)):
    if user.name != "admin":
        raise HTTPException(
            status_code=401,
            detail="Only accessible to admin",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return CODES


@app.get("/state")
async def state():
    return STATE


@app.post("/buzz")
async def buzz(user: User = Depends(user_from_token)):
    async with BUZZLOCK:
        if user.is_player:
            if STATE.buzz == "active":
                STATE.buzz = user.name
            else:
                raise HTTPException(
                    status_code=409,
                    detail="Can't buzz right now",
                )
        elif user.is_admin:
            STATE.buzz = "active"
    return STATE.buzz


@app.delete("/buzz")
async def clear_buzz(user: User = Depends(user_from_token)):
    if not user.is_admin:
        raise HTTPException(
            status_code=401,
            detail="Only accessible to admins",
            headers={"WWW-Authenticate": "Bearer"},
        )
    async with BUZZLOCK:
        STATE.buzz = "inactive"
    return STATE.buzz


@app.get("/ui/buzzer")
async def ui_buzzer(request: Request):  # , user: User = Depends(user_from_token)):
    # FIXME: take from request
    token = [token for token, user in TOKENS.items() if user.name == "left"][0]
    return templates.TemplateResponse(
        "buzzer.html",
        {
            "request": request,
            "disabled": ""
            if STATE.buzz in ("active", "left", "right")
            else "disabled",  # user.name) else "disabled",
            "buzzer_color": (
                "red"
                if STATE.buzz in ("left", "right")  # == user.name
                else "blue"
                if STATE.buzz == "active"
                else "grey"
            ),
            "token": token,
        },
    )
