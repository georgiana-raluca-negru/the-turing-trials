# backend/app/models/__init__.py
# Re-export all models so Alembic and the app can find them in one place.
from app.models.user import User
from app.models.match import Match
from app.models.game_session import GameSession
from app.models.round import Round
from app.models.evidence import Evidence
