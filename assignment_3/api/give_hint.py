# /api/give_hint.py
import re
import logging
from openai import OpenAI
from .conn import chat_gtp_connection

logger = logging.getLogger(__name__)

def give_hint(game_object, difficulty, round_num, previous_hints=None, is_initial_hint=False):
    """
    Generates a hint for the I Spy game based on the current game state.
    """
    if previous_hints is None:
        previous_hints = []

    # 1) Handle the 'initial hint' case quickly
    if is_initial_hint:
        return _initial_hint(difficulty, game_object)

    # 2) Try generating a new hint using ChatGPT
    try:
        hint = _generate_gpt_hint(game_object, difficulty, round_num, previous_hints)
        return hint.strip('"\'')  # Strip quotes if any

    except Exception as e:
        # 3) Fallback if there's an error
        logger.error(f"Error generating hint: {e}")
        return _fallback_hint(difficulty, round_num, game_object)


def _initial_hint(difficulty, game_object):
    """Return an initial hint string immediately, depending on difficulty."""
    color = game_object.get('features', {}).get('color', 'unknown')
    size = game_object.get('features', {}).get('size', 'unknown')

    if difficulty == 1:
        return f"The object I'm thinking of is {color}."
    elif difficulty == 2:
        return f"I spy with my little eye, something that is {size}."
    else:  # difficulty == 3
        return "I spy with my little eye, something in this room."


def _generate_gpt_hint(game_object, difficulty, round_num, previous_hints):
    """Use the OpenAI API to generate a new hint."""
    # 1) Prepare the relevant data
    object_name = game_object.get('name', '')
    dutch_name = game_object.get('dutch_name', '')
    features = game_object.get('features', {})
    color = features.get('color', 'unknown')
    size = features.get('size', 'unknown')
    shape = features.get('shape', 'unknown')

    # 2) Build the user prompt
    prompt = _build_chat_prompt(object_name, dutch_name, color, size, shape,
                                difficulty, round_num, previous_hints)

    # 3) Call the OpenAI API
    api_key = chat_gtp_connection()
    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="gpt-4o-mini",
        max_tokens=100,
        temperature=0.7,
    )
    return response.choices[0].message.content.strip()


def _build_chat_prompt(obj_name, dutch_name, color, size, shape, difficulty, round_num, prev_hints):
    """
    Build a single user prompt for ChatGPT to produce one hint.
    """
    prompt = (
        f"I'm playing an 'I Spy' game where players need to guess this object: "
        f"'{obj_name}' (Dutch: '{dutch_name}'). "
        f"The object has these features: color: {color}, size: {size}, shape: {shape}.\n\n"
        f"This is round {round_num + 1} of the game, difficulty level {difficulty} (1=easy, 3=hard).\n\n"
        f"Previous hints given: {prev_hints}\n\n"
        "Please generate a single hint for this round that:"
    )

    if difficulty == 1:
        if round_num < 2:
            prompt += (
                "\n- Directly mentions ONE specific feature of the object"
                "\n- Suitable for younger players"
                "\n- Is clear and straightforward"
            )
        else:
            prompt += (
                "\n- Gives a more direct clue about the object's use or category"
                "\n- Makes the object fairly easy to guess"
                "\n- Is child-friendly and clear"
            )
    elif difficulty == 2:
        prompt += (
            "\n- Is moderately challenging but fair"
            "\n- Avoids directly stating the most obvious features"
            "\n- Requires some thinking but isn't too cryptic"
            f"\n- Gets more specific in later rounds (this is round {round_num + 1})"
        )
    else:  # difficulty == 3
        prompt += (
            "\n- Is quite challenging and requires creative thinking"
            "\n- Uses indirect references, wordplay, or riddles"
            "\n- Doesn't make the answer too obvious"
            f"\n- Gets slightly more direct in later rounds (this is round {round_num + 1})"
        )

    # Add final instructions for ChatGPT's format
    prompt += (
        "\n\nYour response should be just the hint itself - no explanations, no additional text."
        "\nThe hint should be ONE sentence only, written in simple language suitable for a robot to speak."
        "\nDo not directly reveal what the object is."
    )

    logger.debug("Built prompt for hint generation: %s", prompt)
    return prompt


def _fallback_hint(difficulty, round_num, game_object):
    """Return a fallback hint if the API call fails."""
    color = game_object.get('features', {}).get('color', 'unknown')
    size = game_object.get('features', {}).get('size', 'unknown')
    shape = game_object.get('features', {}).get('shape', 'unknown')

    fallback_hints = {
        1: [
            f"It is {color} in color.",
            f"It is {size} in size.",
            f"It has a {shape} shape.",
            "You might use this object every day.",
            "Look around the room carefully."
        ],
        2: [
            "This object is used for a specific purpose.",
            "You might find this in many homes or offices.",
            f"Think about objects that are {size}.",
            "This object has a specific function.",
            "It's something you might interact with regularly."
        ],
        3: [
            "This object serves a purpose that helps people.",
            "Look beyond the obvious things in the room.",
            "Consider objects you might take for granted.",
            "This object has been around for quite some time.",
            "Think about what you use in your daily activities."
        ]
    }

    difficulty_hints = fallback_hints.get(difficulty, fallback_hints[1])
    hint_index = min(round_num, len(difficulty_hints) - 1)
    return difficulty_hints[hint_index]