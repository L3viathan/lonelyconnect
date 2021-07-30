import os
import random
from asyncio import Lock

import markupsafe
import yaml

from fastapi import FastAPI, Depends, HTTPException, Request, Response, File
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.staticfiles import StaticFiles

from starlette.responses import RedirectResponse

from . import auth
from .models import State, User, BuzzState
from .game import Game

CODES = {}
BUZZLOCK = Lock()
STATE = State()
GAME = Game(STATE)

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def index():
    return RedirectResponse("/ui/login")


@app.post("/login")
async def login(response: Response, request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    # username is actually ignored. These are random single-use non-critical codes.
    username = CODES.pop(form_data.password.upper(), None)
    if not username:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = random_token(32)
    auth.TOKENS[token] = username
    print(f"User {username} logged in with token {token}")
    if request.headers.get("HX-Request"):
        response.headers["HX-Trigger-After-Settle"] = "ocResponse"
    return {"access_token": token, "token_type": "bearer"}


def random_token(length=6):
    return "".join(random.choices("ABCDEFGHKLMNPQRSTUVWXYZ23456789", k=length))


@app.on_event("startup")
async def startup():
    for username in ("admin", "left", "right"):
        auth.USERS[username] = User(name=username)
    if "onlyconnect_admin_code" in os.environ:
        code = os.environ["onlyconnect_admin_code"]
    else:
        code = random_token(6)
        print("admin code:", code)
    CODES[code] = "admin"
    # with open("test.yml") as f:
    #     GAME.load(yaml.load(f))

@app.post("/pair/{username}")
async def pair(username: str, user: User = Depends(auth.admin)):
    code = random_token(6)
    CODES[code] = username
    return code


@app.post("/load")
async def load(user: User = Depends(auth.admin), file: bytes = File(...)):
    global GAME, STATE
    STATE = State()
    GAME = Game(STATE)
    GAME.load(yaml.load(file))


@app.get("/codes")
async def codes(user: User = Depends(auth.admin)):
    return CODES


@app.get("/state")
async def state():
    return STATE


@app.get("/stage")
async def stage():
    return GAME.stage()


@app.get("/secrets")
async def secrets(user: User = Depends(auth.admin)):
    return GAME.secrets()


@app.post("/next")
async def state(user: User = Depends(auth.admin)):
    try:
        return next(GAME)
    except StopIteration:
        return {}


@app.get("/actions")
async def state(user: User = Depends(auth.admin)):
    return GAME.actions()


@app.post("/action/{key}")
async def state(key: str, user: User = Depends(auth.admin)):
    return GAME.action(key)


@app.post("/buzz")
async def buzz(user: User = Depends(auth.player)):
    async with BUZZLOCK:
        if STATE.buzz in ("active", f"active-{user.name}"):
            STATE.buzz = user.name
            GAME.buzz(user.name)
        else:
            raise HTTPException(
                status_code=409,
                detail="Can't buzz right now",
            )
    return STATE.buzz


@app.put("/buzz/{state}")
async def set_buzz(state: BuzzState, user: User = Depends(auth.admin)):
    async with BUZZLOCK:
        STATE.buzz = state.value
    return STATE.buzz


@app.post("/score/{username}")
async def add_to_score(request: Request, username: str, user: User = Depends(auth.admin)):
    form_data = await request.form()
    STATE.points[username] += int(form_data["points"])


@app.post("/name/{username}")
async def add_to_score(request: Request, username: str, user: User = Depends(auth.admin)):
    form_data = await request.form()
    auth.USERS[username].descriptive_name = form_data["teamname"].upper()


@app.get("/ui/stage")
async def ui_stage(request: Request):
    stage = GAME.stage()
    base_dict = {
        "request": request,
        "leftname": auth.USERS["left"].descriptive_name or "left",
        "rightname": auth.USERS["right"].descriptive_name or "right",
        "leftscore": STATE.points["left"],
        "rightscore": STATE.points["right"],
        **stage
    }

    if GAME.part and isinstance(GAME.part, (game.Connections, game.Sequences)):
        return templates.TemplateResponse(
            "connections.html",
            base_dict,
        )
    elif GAME.part and isinstance(GAME.part, game.MissingVowels):
        return templates.TemplateResponse(
            "missing_vowels.html",
            base_dict,
        )
    else:
        return templates.TemplateResponse(
            "stage.html",
            base_dict,
        )


@app.get("/ui/buzzer")
async def ui_buzzer(request: Request, user: User = Depends(auth.player)):
    token = user.get_token(auth.TOKENS)
    return templates.TemplateResponse(
        "buzzer.html",
        {
            "request": request,
            "disabled": ""
            if STATE.buzz in ("active", "left", "right")
            else "disabled",  # user.name) else "disabled",
            "buzz_state": (
                "buzzed"
                if STATE.buzz == user.name
                else "buzzable"
                if STATE.buzz in ("active", f"active-{user.name}")
                else "inactive"
            ),
            **GAME.stage(),
            "authheader": markupsafe.Markup(f""" hx-headers='{{"Authorization": "Bearer {token}"}}' """),
        },
    )


@app.get("/ui/admin")
async def ui_admin(request: Request, user: User = Depends(auth.admin)):
    token = user.get_token(auth.TOKENS)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "actions": GAME.actions(),
            "authheader": markupsafe.Markup(f""" hx-headers='{{"Authorization": "Bearer {token}"}}' """),
            "secrets": GAME.secrets(),
            **GAME.stage(),
        },
    )


@app.get("/ui/login")
async def ui_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        },
    )


@app.post("/ui/redirect")
async def redirect(request: Request):
    form_data = await request.form()
    user = auth.logged_in(form_data.get("access_token"))
    return templates.TemplateResponse(
        "redirect.html",
        {
            "request": request,
            "authheader": markupsafe.Markup(f""" hx-headers='{{"Authorization": "Bearer {form_data["access_token"]}"}}' """),
            "role": "admin" if user.is_admin else "player" if user.is_player else None,
        },
    )
