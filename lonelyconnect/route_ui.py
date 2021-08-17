import markupsafe

from fastapi import FastAPI, Depends, Request
from fastapi.templating import Jinja2Templates

from . import auth, game
from .models import User


subapp = FastAPI()

templates = Jinja2Templates(directory="templates")


@subapp.get("/stage")
async def ui_stage(request: Request):
    stage = game.GAME.stage()
    base_dict = {
        "request": request,
        "leftname": auth.USERS["left"].descriptive_name or "left",
        "rightname": auth.USERS["right"].descriptive_name or "right",
        "leftscore": game.STATE.points["left"],
        "rightscore": game.STATE.points["right"],
        **stage,
    }

    if game.GAME.part and isinstance(
        game.GAME.part, (game.Connections, game.Sequences)
    ):
        return templates.TemplateResponse(
            "connections.html",
            base_dict,
        )
    elif game.GAME.part and isinstance(game.GAME.part, game.MissingVowels):
        return templates.TemplateResponse(
            "missing_vowels.html",
            base_dict,
        )
    else:
        return templates.TemplateResponse(
            "stage.html",
            base_dict,
        )


@subapp.get("/buzzer")
async def ui_buzzer(request: Request, user: User = Depends(auth.player)):
    token = user.get_token(auth.TOKENS)
    return templates.TemplateResponse(
        "buzzer.html",
        {
            "request": request,
            "disabled": ""
            if game.STATE.buzz in ("active", "left", "right")
            else "disabled",  # user.name) else "disabled",
            "buzz_state": (
                "buzzed"
                if game.STATE.buzz == user.name
                else "buzzable"
                if game.STATE.buzz in ("active", f"active-{user.name}")
                else "inactive"
            ),
            **game.GAME.stage(),
            "authheader": markupsafe.Markup(
                f""" hx-headers='{{"Authorization": "Bearer {token}"}}' """
            ),
        },
    )


@subapp.get("/admin")
async def ui_admin(request: Request, user: User = Depends(auth.admin)):
    token = user.get_token(auth.TOKENS)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "actions": game.GAME.actions(),
            "authheader": markupsafe.Markup(
                f""" hx-headers='{{"Authorization": "Bearer {token}"}}' """
            ),
            "secrets": game.GAME.secrets(),
            **game.GAME.stage(),
        },
    )


@subapp.get("/login")
async def ui_login(request: Request):
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
        },
    )


@subapp.post("/redirect")
async def redirect(request: Request):
    form_data = await request.form()
    user = auth.logged_in(form_data.get("access_token"))
    return templates.TemplateResponse(
        "redirect.html",
        {
            "request": request,
            "authheader": markupsafe.Markup(
                f""" hx-headers='{{"Authorization": "Bearer {form_data["access_token"]}"}}' """
            ),
            "role": "admin" if user.is_admin else "player" if user.is_player else None,
        },
    )
