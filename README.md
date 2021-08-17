# LonelyConnect

[![pytest](https://github.com/L3viathan/lonelyconnect/actions/workflows/pytest.yml/badge.svg)](https://github.com/L3viathan/lonelyconnect/actions/workflows/pytest.yml)

This is a fan-made implementation of the BBC quiz show OnlyConnect. It
allows you to write your own riddles and host your own show at home. For partly
technical and partly gameplay reasons, round 3 (the connecting wall) is not
implemented.

In case this isn't clear enough yet: This repository is not associated with the
show at all, and no assets (images, audio, ...) of the original show are used.


# Usage

Start the uvicorn app, e.g. via

    uvicorn lonelyconnect:app

It will print out an admin code. Alternatively, you can set the environment
variable `lonelyconnect_admin_code`.

LonelyConnect requires 4 "devices" (browser tabs):

- One connected to the admin interface (for the quiz master)
- Two for the teams (one each), showing the buzzers
- One for the "stage"; this could be projected on a large screen, it shows
  public information and requires no authentication.

To connect to anything but the stage, just go to the root path (`/`), by
default on port 8000. This will present you with a large text input, in which
you can enter the authentication code. The admin code is obtained as described
above, the codes for the two buzzers can be retrieved via the admin interface.

The stage is available at `/ui/stage`.

Once everyone is connected, you can test the buzzers by setting the buzz mode
manually via the admin interface. During the course of a normal game, the buzz
state (who is allowed to buzz/who has buzzed) will be automatically set through
the game logic.

To start a game, the admin can load a game file.

Afterwards, the admin interface is usable through numeric keyboard shortcuts (as displayed on the dashboard).
