# /api/give_hint.py
import logging
from openai import OpenAI
from .conn import chat_gtp_connection

logger = logging.getLogger(__name__)

def give_hint(game_object, difficulty, round_num, previous_hints=None, is_initial_hint=False):
    """
    Generates a hint for the I Spy game based on the current game state.

    :param dict game_object: Object to hint about with 'name', 'dutch_name', and 'features' (color, size, shape)
    :param int difficulty: Difficulty level (1=easy, 2=medium, 3=hard)
    :param int round_num: Current round number (0-based)
    :param list previous_hints: List of previous hints given (default None)
    :param bool is_initial_hint: Whether this is the initial hint (default False)
    :return: Hint string tailored to the round and difficulty
    :rtype: str
    """
    if previous_hints is None:
        previous_hints = []

    if is_initial_hint:
        return _initial_hint(difficulty, game_object)

    try:
        hint = _generate_gpt_hint(game_object, difficulty, round_num, previous_hints)
        return hint.strip('"\'')
    except Exception as e:
        logger.error(f"Error generating hint: {e}")
        return _fallback_hint(difficulty, round_num, game_object)


def _initial_hint(difficulty, game_object):
    """
    Generate an initial hint in English based on difficulty.

    :param int difficulty: Difficulty level (1=easy, 2=medium, 3=hard)
    :param dict game_object: Object with 'features' containing color and size
    :return: Initial hint string
    :rtype: str
    """
    color = game_object.get('features', {}).get('color', 'unknown')
    size = game_object.get('features', {}).get('size', 'unknown')

    if difficulty == 1:
        return f"The object I'm thinking of is {color}."
    elif difficulty == 2:
        return f"I spy with my little eye, something that is {size}."
    else:
        return "I spy with my little eye, something in this room."


def _generate_gpt_hint(game_object, difficulty, round_num, previous_hints):
    """
    Use the OpenAI API to generate a dynamic hint.

    :param dict game_object: Object with 'name', 'dutch_name', and 'features'
    :param int difficulty: Difficulty level (1=easy, 2=medium, 3=hard)
    :param int round_num: Current round number (0-based)
    :param list previous_hints: List of previous hints
    :return: Generated hint string
    :rtype: str
    """
    object_name = game_object.get('name', '')
    dutch_name = game_object.get('dutch_name', '')
    features = game_object.get('features', {})
    color = features.get('color', 'unknown')
    size = features.get('size', 'unknown')
    shape = features.get('shape', 'unknown')

    prompt = _build_chat_prompt(object_name, dutch_name, color, size, shape,
                                difficulty, round_num, previous_hints)

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
    Construct a prompt for ChatGPT to generate a hint based on round and difficulty.

    :param str obj_name: Object name in English
    :param str dutch_name: Object name in Dutch
    :param str color: Object color
    :param str size: Object size
    :param str shape: Object shape
    :param int difficulty: Difficulty level (1=easy, 2=medium, 3=hard)
    :param int round_num: Current round number (0-based)
    :param list prev_hints: List of previous hints
    :return: Detailed prompt string for the OpenAI API
    :rtype: str
    """
    prompt = (
        f"I'm playing an 'I Spy' game where players guess this object: '{obj_name}' (Dutch: '{dutch_name}'). "
        f"The object has these features: color: {color}, size: {size}, shape: {shape}.\n\n"
        f"This is round {round_num + 1} of the game, difficulty level {difference} (1=easy, 3=hard).\n\n"
        f"Previous hints given: {prev_hints}\n\n"
        "Please generate a single hint for this round that:"
    )

    if round_num == 0:
        prompt += (
            "\n- Is in English only"
            "\n- Mentions the color of the object"
            "\n- Is clear and straightforward for all players"
        )
    elif round_num == 1:
        prompt += (
            "\n- Is in Dutch only, enclosed in <nl>...</nl> tags"
            "\n- Mentions the shape of the object"
            "\n- Uses simple Dutch vocabulary"
            "\n- Avoids contextual clues (e.g., usage or location)"
        )
    else:
        prompt += (
            "\n- Is bilingual: first in Dutch (in <nl>...</nl> tags), then in English"
            "\n- Mentions a feature like size or another attribute"
            "\n- Avoids contextual clues in early rounds"
            f"\n- Gets more specific as rounds progress (this is round {round_num + 1})"
        )

    if difficulty == 1:
        prompt += (
            "\n- Is suitable for younger players"
            "\n- Makes the object fairly easy to guess by round 3"
        )
    elif difficulty == 2:
        prompt += (
            "\n- Is moderately challenging but fair"
            "\n- Requires some thinking"
        )
    else:
        prompt += (
            "\n- Is challenging with indirect references"
            "\n- Requires creative thinking"
        )

    prompt += (
        "\n\nYour response should be just the hint itself - no explanations."
        "\nThe hint should be ONE sentence, simple enough for a robot to speak."
        "\nDo not reveal the object directly."
    )

    logger.debug("Built prompt for hint generation: %s", prompt)
    return prompt


def _fallback_hint(difficulty, round_num, game_object):
    """
    Provide a fallback hint if the API call fails.

    :param int difficulty: Difficulty level (1=easy, 2=medium, 3=hard)
    :param int round_num: Current round number (0-based)
    :param dict game_object: Object with 'features' containing color, size, and shape
    :return: Fallback hint string
    :rtype: str
    """
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