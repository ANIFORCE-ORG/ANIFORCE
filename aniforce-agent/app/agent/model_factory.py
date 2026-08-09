"""Create the configured Agents SDK model implementation."""

from agents.models.openai_chatcompletions import OpenAIChatCompletionsModel
from agents.models.openai_responses import OpenAIResponsesModel


def create_sdk_model(*, api_mode: str, model: str, openai_client):
    if api_mode == "chat_completions":
        return OpenAIChatCompletionsModel(model=model, openai_client=openai_client)
    return OpenAIResponsesModel(model=model, openai_client=openai_client)
