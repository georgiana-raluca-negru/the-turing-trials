# backend/app/schemas/auth.py
"""
Request / response schemas for authentication endpoints.
"""

from pydantic import BaseModel, EmailStr, Field


# ── Registration (US1) ────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


# ── Login ─────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


# ── Token responses ───────────────────────────────────────────────────────────

class TokenResponse(BaseModel):
    """Returned on successful login or token refresh."""
    access_token: str
    token_type: str = "bearer"


class TokenPair(BaseModel):
    """Returned on first login — includes the refresh token in the body
    (the router also sets it as an httpOnly cookie)."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


# ── OAuth ─────────────────────────────────────────────────────────────────────

class OAuthRedirectResponse(BaseModel):
    """URL the frontend should redirect the browser to."""
    authorization_url: str
