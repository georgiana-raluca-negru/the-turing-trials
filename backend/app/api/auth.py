# backend/app/api/auth.py
"""
Authentication router — US1, US2.

Endpoints:
  POST /api/auth/register          US1 — email + password registration
  POST /api/auth/login             US1 — returns JWT pair
  POST /api/auth/logout            US2 — clears refresh cookie (stateless)
  POST /api/auth/refresh           US2 — issues new access token from cookie
  GET  /api/auth/oauth/{provider}  US1 — returns provider's authorization URL
  GET  /api/auth/oauth/{provider}/callback  US1 — handles OAuth callback
"""

from datetime import timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_from_refresh_cookie
from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    OAuthRedirectResponse,
    RegisterRequest,
    TokenResponse,
    TokenPair,
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# ── Helpers ───────────────────────────────────────────────────────────────────

REFRESH_COOKIE_KEY = "refresh_token"
REFRESH_COOKIE_MAX_AGE = int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds())


def _set_refresh_cookie(response: Response, refresh_token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=refresh_token,
        httponly=True,
        secure=False,        # set True in production (HTTPS only)
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path="/api/auth/refresh",
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(key=REFRESH_COOKIE_KEY, path="/api/auth/refresh")


# ── US1 — Registration ────────────────────────────────────────────────────────

@router.post(
    "/register",
    response_model=TokenPair,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user with email and password (US1)",
)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    # Check for duplicate email or username
    existing = await db.execute(
        select(User).where(
            (User.email == body.email) | (User.username == body.username)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=hash_password(body.password),
        is_active=True,
        is_verified=False,   # future: send verification email
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh_token)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ── US1 — Login ───────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenPair,
    summary="Log in with email and password (US1)",
)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    result = await db.execute(select(User).where(User.email == body.email))
    user: User | None = result.scalar_one_or_none()

    if user is None or user.hashed_password is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh_token)

    return TokenPair(
        access_token=access_token,
        refresh_token=refresh_token,
    )


# ── US2 — Logout ──────────────────────────────────────────────────────────────

@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Log out — clears the refresh token cookie (US2)",
)
async def logout(response: Response) -> None:
    """
    Stateless logout: the server clears the httpOnly refresh cookie.
    The client is responsible for dropping its access token from memory.
    (A Redis blacklist can be added here later for full server-side revocation.)
    """
    _clear_refresh_cookie(response)


# ── US2 — Refresh access token ────────────────────────────────────────────────

@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh the access token using the httpOnly cookie (US2)",
)
async def refresh_access_token(
    response: Response,
    user: User = Depends(get_current_user_from_refresh_cookie),
) -> TokenResponse:
    """
    Exchange a valid refresh-token cookie for a new short-lived access token.
    Rotation: also issues a fresh refresh token to extend the session.
    """
    new_access = create_access_token(str(user.id))
    new_refresh = create_refresh_token(str(user.id))   # token rotation
    _set_refresh_cookie(response, new_refresh)

    return TokenResponse(access_token=new_access)


# ── US1 — OAuth — get authorization URL ───────────────────────────────────────

_OAUTH_PROVIDERS = {
    "google": {
        "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "client_id_key": "GOOGLE_CLIENT_ID",
        "redirect_uri_key": "GOOGLE_REDIRECT_URI",
        "scope": "openid email profile",
    },
    "github": {
        "auth_url": "https://github.com/login/oauth/authorize",
        "client_id_key": "GITHUB_CLIENT_ID",
        "redirect_uri_key": "GITHUB_REDIRECT_URI",
        "scope": "read:user user:email",
    },
}


@router.get(
    "/oauth/{provider}",
    response_model=OAuthRedirectResponse,
    summary="Get the OAuth authorization URL for Google or GitHub (US1)",
)
async def oauth_redirect(provider: str) -> OAuthRedirectResponse:
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider: {provider}")

    cfg = _OAUTH_PROVIDERS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    redirect_uri = getattr(settings, cfg["redirect_uri_key"])

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider.capitalize()} OAuth is not configured on this server",
        )

    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "scope": cfg["scope"],
        "response_type": "code",
    }
    if provider == "google":
        params["access_type"] = "offline"

    from urllib.parse import urlencode
    auth_url = f"{cfg['auth_url']}?{urlencode(params)}"
    return OAuthRedirectResponse(authorization_url=auth_url)


# ── US1 — OAuth — callback ────────────────────────────────────────────────────

@router.get(
    "/oauth/{provider}/callback",
    summary="Handle OAuth callback from Google or GitHub (US1)",
)
async def oauth_callback(
    provider: str,
    code: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange the authorization code for an OAuth access token,
    fetch the user's profile, upsert a User row, and issue our own JWTs.
    """
    if provider not in _OAUTH_PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown provider: {provider}")

    cfg = _OAUTH_PROVIDERS[provider]
    client_id = getattr(settings, cfg["client_id_key"])
    client_secret = getattr(settings, f"{provider.upper()}_CLIENT_SECRET")
    redirect_uri = getattr(settings, cfg["redirect_uri_key"])

    if not client_id or not client_secret:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=f"{provider.capitalize()} OAuth is not configured",
        )

    async with httpx.AsyncClient() as client:
        if provider == "google":
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            userinfo_resp.raise_for_status()
            info = userinfo_resp.json()
            oauth_sub = info["sub"]
            email = info["email"]
            username = info.get("name", email.split("@")[0]).replace(" ", "_")[:50]

        else:  # github
            token_resp = await client.post(
                "https://github.com/login/oauth/access_token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": redirect_uri,
                },
                headers={"Accept": "application/json"},
            )
            token_resp.raise_for_status()
            token_data = token_resp.json()
            userinfo_resp = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token_data['access_token']}"},
            )
            userinfo_resp.raise_for_status()
            info = userinfo_resp.json()
            oauth_sub = str(info["id"])
            email = info.get("email") or f"{info['login']}@github.local"
            username = info["login"][:50]

    # Upsert: find existing user by oauth_sub or email
    result = await db.execute(
        select(User).where(
            (User.oauth_sub == oauth_sub) & (User.oauth_provider == provider)
        )
    )
    user: User | None = result.scalar_one_or_none()

    if user is None:
        # Try to match by email (user might have registered with email before)
        result2 = await db.execute(select(User).where(User.email == email))
        user = result2.scalar_one_or_none()
        if user:
            # Link OAuth to existing account
            user.oauth_provider = provider
            user.oauth_sub = oauth_sub
        else:
            # Create brand-new OAuth user
            # Handle duplicate username by appending provider suffix
            base_username = username
            suffix = 0
            while True:
                check = await db.execute(select(User).where(User.username == username))
                if check.scalar_one_or_none() is None:
                    break
                suffix += 1
                username = f"{base_username}_{suffix}"

            user = User(
                username=username,
                email=email,
                hashed_password=None,
                oauth_provider=provider,
                oauth_sub=oauth_sub,
                is_active=True,
                is_verified=True,   # OAuth emails are pre-verified
            )
            db.add(user)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token(str(user.id))
    refresh_token = create_refresh_token(str(user.id))
    _set_refresh_cookie(response, refresh_token)

    # In a real app: redirect to the frontend with the access token as a query param
    # or store in a short-lived code. For now, return JSON.
    return {"access_token": access_token, "token_type": "bearer", "provider": provider}
