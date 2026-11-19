
from datetime import datetime, timezone

import aiohttp_jinja2
from aiohttp import web
from aiohttp_session import get_session


async def index(request: web.Request) -> web.Response:
    """Render the main page."""
    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {"config": request.app.get("config")},
    )


async def login(request: web.Request) -> web.Response:
    """Render the login page and record the visit in the session."""
    session = await get_session(request)
    last_visit = datetime.now(timezone.utc).isoformat()
    session["last_visit"] = last_visit

    return aiohttp_jinja2.render_template(
        "login.html",
        request,
        {"text": f"Login Page\nLast visited: {last_visit}"},
    )


async def login_post(request: web.Request) -> web.Response:
    """Accept login form data and redirect to the main page."""
    data = await request.post()
    login_value = data.get("login")
    password = data.get("password")

    if not login_value or not password:
        raise web.HTTPBadRequest(
            text="Login and password are required"
        )

    session = await get_session(request)
    session["user"] = {"login": str(login_value)}

    raise web.HTTPFound(
        location=request.app.router["index"].url_for()
    )


async def signup(request: web.Request) -> web.Response:
    """Render a minimal signup page."""
    return web.Response(
        text="Signup page",
        content_type="text/plain",
    )
