import dotenv

from litellm import completion

dotenv.load_dotenv()


def match(text: str, condition: str, text_type: str = "text") -> bool:
    text_type = text_type.lower()
    response = completion(
        model="gpt-5-mini",
        reasoning_effort="low",
        messages=[
            {
                "role": "user",
                "content": f"Does the following {text_type} match the condition? Only respond with 'yes' or 'no'.\n\n{text_type.capitalize()}: {text}\n\nCondition: {condition}",
            }
        ],
    )
    answer = response["choices"][0]["message"]["content"].lower()
    if answer == "yes":
        return True
    elif answer == "no":
        return False
    else:
        raise ValueError(f"Invalid answer: {answer}")
