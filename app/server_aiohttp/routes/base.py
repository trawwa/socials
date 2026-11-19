
from app.server_aiohttp.handlers.base import (
    index,
    login,
    login_post,
    signup,
)


def setup_routes(app):
    app.router.add_get("/", index, name="index")
    app.router.add_get("/login", login, name="login")
    app.router.add_post("/login", login_post)
    app.router.add_get("/signup", signup, name="signup")
