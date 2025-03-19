# /api/api_handler.py
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


def choose_object(objects: dict, difficulty: int):
    """
    Chooses an object based on difficulty and the recognized objects during the scanning routine.
    Returns detailed information about the chosen object including features and Dutch translation.

    :param objects: dict containing objects with their features, confidence and position data
    :param difficulty: (1-3) difficulty level where 1 is easy, 3 is hard
    :return: dict with detailed object information
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)

        # Filter to keep only chatgpt objects since we want more detailed descriptions
        chatgpt_objects = {k: v for k, v in objects.items() if v.get('source') == 'chatgpt'}

        if not chatgpt_objects:
            logger.warning("No ChatGPT-detected objects available for selection")
            return None

        # Prepare a structured prompt for better results
        prompt = (
            f"I need to choose an object for an 'I Spy' game based on difficulty level {difficulty} (1=easy, 3=hard). "
            f"Here are the detected objects with their positions and confidence: {chatgpt_objects}\n\n"
            f"Please select ONE appropriate object based on the following criteria:\n"
            f"- For difficulty 1 (easy): Choose objects with simple, common names that children might know, with distinctive colors or shapes\n"
            f"- For difficulty 2 (medium): Choose objects with moderate complexity or less distinctive features\n"
            f"- For difficulty 3 (hard): Choose objects with complex names, less common objects, or objects with subtle features\n\n"
            f"For the selected object, provide the following information in a structured JSON format:\n"
            f"1. 'name': The English name of the object\n"
            f"2. 'dutch_name': The Dutch translation of the object name\n"
            f"3. 'confidence': The confidence score from the original detection\n"
            f"4. 'position_id': The position identifier where the object was detected (e.g., '2_left')\n"
            f"5. 'features': A dictionary containing:\n"
            f"   - 'color': The primary color(s) of the object\n"
            f"   - 'size': The approximate size description (small, medium, large)\n"
            f"   - 'shape': The shape description of the object\n\n"
            f"ONLY return the JSON object with this information, no additional text."
        )

        logger.debug("Built prompt for object selection: %s", prompt)

        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="gpt-4o-mini",
            max_tokens=300,
            temperature=0.3  # Lower temperature for more consistent JSON responses
        )

        # Extract the response text
        response_text = response.choices[0].message.content.strip()

        try:
            # Parse JSON response
            import json
            detailed_object = json.loads(response_text)
            logger.debug("Selected object with details: %s", detailed_object)

            # Add any missing fields from the original object data if possible
            object_name = detailed_object.get('name')
            for obj_id, obj_data in chatgpt_objects.items():
                if obj_data.get('name').lower() == object_name.lower():
                    # Copy original detection data that might be missing
                    for key in ['yaw', 'pitch', 'turn', 'cumulative_rotation', 'orientation', 'position_id']:
                        if key in obj_data and key not in detailed_object:
                            detailed_object[key] = obj_data[key]

                    # Handle the case where ChatGPT returned 'position' instead of 'position_id'
                    if 'position' in detailed_object and 'position_id' not in detailed_object:
                        detailed_object['position_id'] = detailed_object.pop('position')

                    break

            # Final check to ensure we have position_id
            if 'position' in detailed_object and 'position_id' not in detailed_object:
                detailed_object['position_id'] = detailed_object.pop('position')

            return detailed_object
        except json.JSONDecodeError:
            # If parsing fails, try to extract JSON from text
            import re
            json_match = re.search(r'({.*})', response_text, re.DOTALL)
            if json_match:
                try:
                    detailed_object = json.loads(json_match.group(1))
                    logger.debug("Extracted object from text: %s", detailed_object)
                    return detailed_object
                except:
                    logger.error("Failed to parse extracted JSON")

            logger.error("Failed to parse ChatGPT response as JSON: %s", response_text)
            return None

    except Exception as e:
        logger.error("Error in choose_object: %s", e)
        return None


def give_hint(difficulty, round_n, previous_hints):
