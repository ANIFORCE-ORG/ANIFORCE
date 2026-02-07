from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    game_description: str
    game_type: str


class MessageRequest(BaseModel):
    content: str
