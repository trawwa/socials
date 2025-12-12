from app.server_aiohttp.handlers.base import index, login, signup


def setup_routes(app):
    app.router.add_get("/", index)
    app.router.add_post("/login", login)
    app.router.add_post("/signup", signup)
