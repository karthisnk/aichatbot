from typing import Any

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    role: str
    text: str


class ChatRequest(BaseModel):
    question: str
    patient_id: str | None = None
    app: str | None = None
    filters: dict[str, Any] | None = Field(default=None)
    history: list[ChatTurn] = Field(default_factory=list)

    def to_where(self) -> dict[str, Any] | None:
        where: dict[str, Any] = {}

        if self.filters:
            where.update(self.filters)

        if self.patient_id:
            where["patient_id"] = self.patient_id

        if self.app:
            where["app"] = self.app

        return where or None
