from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    message_id: str
    question: str
    answer: str
    created_at: str
