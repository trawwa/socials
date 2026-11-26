from app.server_aiohttp.handlers.base import (
    IndexView,
    LoginView,
    LogoutView,
    SignupView,
)


def setup_routes(app):
    app.router.add_view("/", IndexView, name="index")
    app.router.add_view("/login", LoginView, name="login")
    app.router.add_view("/logout", LogoutView, name="logout")
    app.router.add_view("/signup", SignupView, name="signup")
