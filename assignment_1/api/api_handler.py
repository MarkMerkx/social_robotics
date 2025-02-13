import re
import logging
from openai import OpenAI
from .conn import chat_gtp_connection

logger = logging.getLogger(__name__)

def build_prompt(previous_guesses, last_user_input):
    """
    Build the prompt using previous rounds and the latest user response.
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
    Silences extra HTTP debugging and handles errors.
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)
        prompt = build_prompt(previous_guesses, last_user_input)
        logger.debug("Built prompt for guess: %s", prompt)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=200,
            temperature=0.8
        )
        raw_response = response.choices[0].message.content.strip()
        logger.debug("Raw response from ChatGPT: %s", raw_response)
        return parse_response(raw_response)
    except Exception as e:
        logger.error("Error in guess call: %s", e)
        return "I'm sorry, I couldn't generate a question."


def answer_question_with_api(chosen_word, question):
    """
    Uses the ChatGPT API to answer a yes/no question about the chosen word.
    The prompt tells the model the secret word and asks it to respond only "yes" or "no."

    :param chosen_word: The secret word.
    :param question: The user's yes/no question.
    :return: "yes" or "no" (or "I don't know" on error).
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)
        prompt = (
            f"The secret word is '{chosen_word}'.\n"
            f"Answer the following question with only 'yes' or 'no':\n"
            f"Question: {question}\n"
        )
        logger.debug("Built prompt for answer: %s", prompt)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=20,
            temperature=0
        )
        raw_response = response.choices[0].message.content.strip().lower()
        logger.debug("Raw answer response: %s", raw_response)
        if "yes" in raw_response:
            return "yes"
        elif "no" in raw_response:
            return "no"
        else:
            return "I don't know"
    except Exception as e:
        logger.error("Error in answer_question_with_api: %s", e)
        return "I don't know"


def generate_secret_word():
    """
    Uses the ChatGPT API to generate a simple secret word.
    The prompt instructs the model to choose one common word.
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)
        prompt = (
            "Please choose one simple, common English word (preferably 4-8 letters) that is not too complex, "
            "and output only the word."
        )
        logger.debug("Built prompt for secret word: %s", prompt)
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=10,
            temperature=0.5
        )
        word = response.choices[0].message.content.strip().lower()
        logger.debug("Generated secret word: %s", word)
        return word
    except Exception as e:
        logger.error("Error in generate_secret_word: %s", e)
        # Fallback to a random word from a hardcoded list.
        return "apple"