import os
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8001/callback")

oauth = OAuth()
oauth.register(
    "auth0",
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    client_kwargs={"scope": "openid profile email"},
    server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
)


async def login_route(request: Request):
    return await oauth.auth0.authorize_redirect(request, AUTH0_CALLBACK_URL)


async def callback_route(request: Request):
    token = await oauth.auth0.authorize_access_token(request)
    request.session["user"] = dict(token["userinfo"])
    return RedirectResponse(url="/")


async def logout_route(request: Request):
    request.session.clear()
    base_url = AUTH0_CALLBACK_URL.rsplit("/callback", 1)[0]
    params = urlencode({"returnTo": base_url, "client_id": AUTH0_CLIENT_ID})
    return RedirectResponse(url=f"https://{AUTH0_DOMAIN}/v2/logout?{params}")


class AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = {"/login", "/callback"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self._PUBLIC or path.startswith("/static"):
            return await call_next(request)
        if not request.session.get("user"):
            return RedirectResponse(url="/login")
        return await call_next(request)
