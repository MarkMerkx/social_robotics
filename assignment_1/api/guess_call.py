import re
from openai import OpenAI
from .conn import chat_gtp_connection


def build_prompt(previous_guesses, last_user_input):
    """
    Build the prompt using previous guesses and the latest user input.
    The output should be delimited by <<< and >>>.
    """
    prompt = (
        "You are a guessing game assistant. The player is thinking of a word, "
        "and your goal is to guess it by asking yes/no questions. "
        "Use the feedback from previous rounds to refine your questions.\n\n"
        "Previous rounds:\n"
    )
    if previous_guesses:
        for idx, entry in enumerate(previous_guesses, start=1):
            prompt += f"{idx}. Question: {entry['guess']} | Feedback: {entry['feedback']}\n"
    else:
        prompt += "None\n"

    if last_user_input:
        prompt += f"\nThe latest user response was: \"{last_user_input}\"\n"

    prompt += (
        "\nBased on this context, propose your next yes/no question to narrow down the word. "
        "Output only the question enclosed between <<< and >>>. For example:\n"
        "<<<Is it an animal?>>>\n"
    )
    return prompt


def parse_response(response_text):
    """
    Extracts the text between <<< and >>>. If not found, returns the full response.
    """
    match = re.search(r'<<<(.*?)>>>', response_text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return response_text.strip()


def guess(last_user_input, previous_guesses):
    """
    Calls the ChatGPT API with a templated prompt to generate the next guess.

    :param last_user_input: The most recent answer/feedback from the user.
    :param previous_guesses: A list of previous rounds with 'guess' and 'feedback'.
    :return: The next yes/no question as a string.
    """
    api_key = chat_gtp_connection()
    client = OpenAI(api_key=api_key)
    prompt = build_prompt(previous_guesses, last_user_input)

    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4",
        max_tokens=200,
        temperature=0.8
    )
    raw_response = response.choices[0].message.content.strip()
    return parse_response(raw_response)