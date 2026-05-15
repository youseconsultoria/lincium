import os
from urllib.parse import urlencode

from authlib.integrations.starlette_client import OAuth
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_CLIENT_ID = os.getenv("AUTH0_CLIENT_ID", "")
AUTH0_CLIENT_SECRET = os.getenv("AUTH0_CLIENT_SECRET", "")
AUTH0_CALLBACK_URL = os.getenv("AUTH0_CALLBACK_URL", "http://localhost:8000/callback")

# Namespace do custom claim injetado pela Auth0 Action (Post Login).
TENANT_CLAIM = "https://lincium.com.br/tenant_id"

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
    userinfo = dict(token["userinfo"])
    # Move o custom claim para a chave curta "tenant_id" na sessão.
    userinfo["tenant_id"] = userinfo.pop(TENANT_CLAIM, None)
    request.session["user"] = userinfo
    next_url = request.session.pop("next", "/")
    return RedirectResponse(url=next_url)


async def logout_route(request: Request):
    request.session.clear()
    base_url = AUTH0_CALLBACK_URL.rsplit("/callback", 1)[0]
    params = urlencode({"returnTo": base_url, "client_id": AUTH0_CLIENT_ID})
    return RedirectResponse(url=f"https://{AUTH0_DOMAIN}/v2/logout?{params}")


class AuthMiddleware(BaseHTTPMiddleware):
    _PUBLIC = {"/login", "/callback"}

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self._PUBLIC or path.startswith("/static") or path.startswith("/app/assets"):
            return await call_next(request)
        if not request.session.get("user"):
            request.session["next"] = path
            return RedirectResponse(url="/login")
        return await call_next(request)
