import random
from asyncio import Lock

from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm

from starlette.responses import RedirectResponse

from . import auth
from .models import State, User, BuzzState

CODES = {}
TOKENS = {}
BUZZLOCK = Lock()
STATE = State()

app = FastAPI()

templates = Jinja2Templates(directory="templates")


@app.get("/")
async def index():
    return RedirectResponse("/ui/login")


@app.post("/login")
async def login(response: Response, request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
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
    print(f"User {user} logged in with token {token}")
    if user.is_player:
        setattr(STATE, username, user)
    if request.headers.get("HX-Request"):
        response.headers["HX-Trigger-After-Settle"] = "ocResponse"
    return {"access_token": token, "token_type": "bearer"}


def random_token(length=6):
    return "".join(random.choices("ABCDEFGHKLMNPQRSTUVWXYZ23456789", k=length))


@app.on_event("startup")
async def startup():
    for username in ("admin", "left", "right"):
        code = random_token(6)
        print(f"CODE for {username}:", code)
        CODES[code] = username


@app.get("/codes")
async def codes(user: User = Depends(auth.admin)):
    # if user.name != "admin":
    #     raise HTTPException(
    #         status_code=401,
    #         detail="Only accessible to admin",
    #         headers={"WWW-Authenticate": "Bearer"},
    #     )
    return CODES


@app.get("/state")
async def state():
    return STATE


@app.post("/buzz")
async def buzz(user: User = Depends(auth.player)):
    async with BUZZLOCK:
        if STATE.buzz in ("active", f"active-{user.name}"):
            STATE.buzz = user.name
        else:
            raise HTTPException(
                status_code=409,
                detail="Can't buzz right now",
            )
    return STATE.buzz


@app.put("/buzz/<state>")
async def set_buzz(state: BuzzState, user: User = Depends(auth.admin)):
    async with BUZZLOCK:
        STATE.buzz = state
    return STATE.buzz


@app.post("/ui/buzzer")
async def ui_buzzer(request: Request, user: User = Depends(auth.player)):
    token = user.get_token(TOKENS)
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
    user = user_from_token(form_data.get("access_token"))
    return templates.TemplateResponse(
        "redirect.html",
        {
            "request": request,
            "token": form_data["access_token"],
            "role": "admin" if user.is_admin else "player" if user.is_player else None,
        },
    )
