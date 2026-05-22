from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class ActorRole(str, Enum):
    PROSECUTION = "prosecution"
    DEFENSE = "defense"
    JUDGE = "judge"


class ActorController(str, Enum):
    HUMAN = "human"
    AI = "ai"


class ActorConfiguration(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    prosecution: ActorController = ActorController.AI
    defense: ActorController = ActorController.AI
    judge: ActorController = ActorController.AI

    def controller_for(self, role: ActorRole) -> ActorController:
        if role == ActorRole.PROSECUTION:
            return self.prosecution
        if role == ActorRole.DEFENSE:
            return self.defense
        return self.judge
