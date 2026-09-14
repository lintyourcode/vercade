import dotenv
from pydantic_ai import Agent

dotenv.load_dotenv()

# The model is checked on first use rather than at import so that offline
# tests (which import this module) can be collected without OPENAI_API_KEY.
_judge = Agent(
    "openai:gpt-5-mini", model_settings={"thinking": "low"}, defer_model_check=True
)


async def match(text: str, condition: str, text_type: str = "text") -> bool:
    text_type = text_type.lower()
    result = await _judge.run(
        f"Does the following {text_type} match the condition? Only respond with 'yes' or 'no'.\n\n{text_type.capitalize()}: {text}\n\nCondition: {condition}"
    )
    answer = result.output.strip().lower()
    if answer == "yes":
        return True
    elif answer == "no":
        return False
    else:
        raise ValueError(f"Invalid answer: {answer}")
