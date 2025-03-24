# /api/api_handler.py
import re
import logging
from openai import OpenAI
from .conn import chat_gtp_connection
from .give_hint import give_hint
import random

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
    Uses image reference when available to improve feature accuracy, with diverse selection across all difficulties.

    :param objects: dict containing objects with their features, confidence and position data
    :param difficulty: (1-3) difficulty level where 1 is easy, 3 is hard
    :return: dict with detailed object information
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)

        # Filter to keep only ChatGPT-detected objects for detailed descriptions
        chatgpt_objects = {k: v for k, v in objects.items() if v.get('source') == 'chatgpt'}

        if not chatgpt_objects:
            logger.warning("No ChatGPT-detected objects available for selection")
            return None

        # Define priority lists for object names and colors
        simple_objects = ['ball', 'bottle', 'cup', 'book', 'toy', 'pen']
        dull_colors = ['black', 'gray', 'white', 'brown', 'unknown']

        # Select candidates with a relaxed confidence threshold of 0.75
        candidates = []
        for obj_id, obj_data in chatgpt_objects.items():
            obj_name = obj_data.get('name', '').lower()
            features = obj_data.get('features', {})
            color = features.get('color', 'unknown').lower()
            confidence = obj_data.get('confidence', 0)

            # Only include objects with confidence >= 0.75
            if confidence < 0.75:
                logger.debug(f"Excluding {obj_name} due to low confidence: {confidence}")
                continue

            # Assign a score based on difficulty and object characteristics
            score = 0
            if difficulty == 1:  # Easy: prioritize vivid, colorful, simple objects
                if any(simple in obj_name for simple in simple_objects):
                    score += 2  # Higher priority for simple, engaging objects
                if color not in dull_colors:
                    score += 1  # Boost for vivid colors
            elif difficulty == 2:  # Medium: moderately complex objects
                if not any(simple in obj_name for simple in ['chair', 'table', 'desk']):
                    score += 1
                if color not in dull_colors:
                    score += 1
            else:  # Hard: complex or unusual objects
                if not any(simple in obj_name for simple in ['chair', 'table', 'bottle', 'cup', 'book', 'desk', 'monitor', 'keyboard']):
                    score += 1

            candidates.append((obj_id, obj_data, score))

        # Log all candidates for debugging
        logger.debug("All candidates with scores: %s", [(obj_id, obj_data['name'], score) for obj_id, obj_data, score in candidates])

        # If no candidates meet criteria, relax constraints for difficulty 1
        if not candidates and difficulty == 1:
            logger.debug("No candidates found, relaxing constraints for difficulty 1")
            for obj_id, obj_data in chatgpt_objects.items():
                confidence = obj_data.get('confidence', 0)
                if confidence >= 0.75:
                    candidates.append((obj_id, obj_data, 1))  # Default score of 1

        if not candidates:
            logger.warning("No suitable candidates found even with relaxed constraints")
            return None

        # Sort by confidence and take top 5 (or fewer if less than 5 candidates)
        candidates.sort(key=lambda x: x[1].get('confidence', 0), reverse=True)
        top_candidates = candidates[:min(5, len(candidates))]

        # Log top candidates
        logger.debug("Top 5 candidates: %s", [(obj_id, obj_data['name'], score) for obj_id, obj_data, score in top_candidates])

        # Weighted random selection from top candidates based on scores
        total_score = sum(score for _, _, score in top_candidates)
        if total_score > 0:  # Avoid division by zero
            selection_weights = [score / total_score for _, _, score in top_candidates]
        else:
            selection_weights = [1 / len(top_candidates)] * len(top_candidates)  # Equal weights if no scores

        selected_candidate = random.choices(top_candidates, weights=selection_weights, k=1)[0]
        selected_obj_id, selected_obj_data, selected_score = selected_candidate

        # Log the selected object
        logger.debug("Selected object: %s with score %d", selected_obj_data['name'], selected_score)

        # Get image if available
        has_image = False
        image_base64 = None
        position_id = selected_obj_data.get('position_id')
        name = selected_obj_data.get('name')

        if position_id and name:
            import glob
            possible_images = glob.glob(f"scan_images/pos_{position_id}*{name}*.jpg")
            if possible_images:
                image_path = possible_images[0]
                logger.info(f"Found image for object: {image_path}")
                try:
                    import base64
                    with open(image_path, "rb") as img_file:
                        image_base64 = base64.b64encode(img_file.read()).decode('utf-8')
                        has_image = True
                except Exception as e:
                    logger.error(f"Error encoding image: {e}")

        # Prepare prompt based on image availability
        if has_image:
            logger.info("Using image-based analysis for object features")
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"I need to choose an object for an 'I Spy' game for difficulty level {difficulty} (1=easy, 3=hard). "
                                f"Analyze the image of '{selected_obj_data.get('name')}' and provide detailed info.\n\n"
                                f"For the object, return a JSON with:\n"
                                f"1. 'name': English name\n"
                                f"2. 'dutch_name': Dutch translation\n"
                                f"3. 'confidence': {selected_obj_data.get('confidence', 0.9)}\n"
                                f"4. 'position_id': '{selected_obj_data.get('position_id', '')}'\n"
                                f"5. 'features': Dict with:\n"
                                f"   - 'color': Exact color(s) from the image\n"
                                f"   - 'size': Small, medium, or large\n"
                                f"   - 'shape': Shape description\n\n"
                                f"Base color ONLY on the image. Be precise. Return ONLY the JSON."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                        }
                    ]
                }
            ]
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=400,
                temperature=0.3
            )
        else:
            logger.info("Using text-based analysis for object selection")
            prompt = (
                f"I need to choose an object for an 'I Spy' game for difficulty level {difficulty} (1=easy, 3=hard). "
                f"Detected objects: {dict((obj_id, obj_data) for obj_id, obj_data, _ in top_candidates)}\n\n"
                f"Select ONE object, prioritizing:\n"
                f"- Difficulty 1 (easy): Simple, vivid objects (e.g., bright colors like red, green, blue; unique shapes) for young players\n"
                f"- Difficulty 2 (medium): Moderately complex objects with distinct features\n"
                f"- Difficulty 3 (hard): Complex or unusual objects\n\n"
                f"Return a JSON with:\n"
                f"1. 'name': English name\n"
                f"2. 'dutch_name': Dutch translation\n"
                f"3. 'confidence': Original confidence score\n"
                f"4. 'position_id': Position (e.g., '2_left')\n"
                f"5. 'features': Dict with:\n"
                f"   - 'color': Primary color(s) (e.g., 'red', not 'unknown')\n"
                f"   - 'size': Small, medium, large\n"
                f"   - 'shape': Shape (e.g., 'round')\n\n"
                f"ONLY return the JSON."
            )
            messages = [{"role": "user", "content": prompt}]
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=400,
                temperature=0.3
            )

        # Parse response
        response_text = response.choices[0].message.content.strip()
        import re
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            import json
            detailed_object = json.loads(json_match.group(0))
            logger.debug("Selected object details: %s", detailed_object)

            # Add missing fields
            object_name = detailed_object.get('name')
            for obj_id, obj_data in chatgpt_objects.items():
                if obj_data.get('name').lower() == object_name.lower():
                    for key in ['yaw', 'pitch', 'turn', 'cumulative_rotation', 'orientation', 'position_id']:
                        if key in obj_data and key not in detailed_object:
                            detailed_object[key] = obj_data[key]
                    break

            # Ensure specific features
            features = detailed_object.get('features', {})
            if any(features.get(k) == 'unknown' for k in ['color', 'size', 'shape']):
                if features.get('color') == 'unknown':
                    features['color'] = 'multicolored'
                if features.get('size') == 'unknown':
                    features['size'] = 'medium'
                if features.get('shape') == 'unknown':
                    features['shape'] = 'irregular'
                detailed_object['features'] = features

            detailed_object['features_from_image'] = has_image
            return detailed_object
        else:
            logger.error("No JSON in response: %s", response_text)
            return None

    except Exception as e:
        logger.error("Error in choose_object: %s", e)
        return None


def start_i_spy_game(game_object, difficulty=1):
    """
    Start an I Spy game with an initial hint.

    :param game_object: The selected object for the game
    :type game_object: dict
    :param difficulty: Difficulty level (1-3)


    :type difficulty: int
    :return: Initial hint and introduction text
    :rtype: tuple(str, str)
    """
    # Create introduction based on difficulty
    if difficulty == 1:
        intro = "Let's play I Spy! I'm thinking of something in this room."
    elif difficulty == 2:
        intro = "Ready for a game of I Spy? I've spotted something interesting!"
    else:
        intro = "I challenge you to a difficult game of I Spy. See if you can guess what I'm thinking of."

    # Generate the initial hint
    initial_hint = give_hint(game_object, difficulty, 0, [], is_initial_hint=True)

    return intro, initial_hint


def process_guess(guess, game_object, round_num, previous_hints):
    """
    Process a player's guess in the I Spy game.

    :param guess: The player's guess
    :type guess: str
    :param game_object: The object to be guessed
    :type game_object: dict
    :param round_num: Current round number
    :type round_num: int
    :param previous_hints: Previous hints given
    :type previous_hints: list
    :return: Response to the guess and whether it was correct
    :rtype: tuple(str, bool)
    """
    try:
        api_key = chat_gtp_connection()
        client = OpenAI(api_key=api_key)

        # Extract target object information
        object_name = game_object.get('name', '').lower()
        dutch_name = game_object.get('dutch_name', '').lower()
        guess = guess.lower()

        # Direct match check
        is_correct = (
                guess == object_name or
                guess == dutch_name or
                object_name in guess or
                dutch_name in guess
        )

        # For less obvious matches, use the API
        if not is_correct and (len(guess) > 3):  # Only for substantial guesses
            prompt = (
                f"In an 'I Spy' game, the target object is: '{object_name}' (Dutch: '{dutch_name}'). "
                f"The player guessed: '{guess}'.\n\n"
                f"Determine if the player's guess is close enough to be considered correct. "
                f"Answer with ONLY 'yes' or 'no'."
            )

            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="gpt-4o-mini",
                max_tokens=10,
                temperature=0.3
            )

            answer = response.choices[0].message.content.strip().lower()
            is_correct = is_correct or ('yes' in answer)

        # Generate appropriate response based on correctness
        if is_correct:
            responses = [
                f"Yes, that's right! I was thinking of the {object_name}!",
                f"Correct! The {object_name} is what I had in mind!",
                f"You got it! It's the {object_name}!",
                f"Well done! You guessed it - the {object_name}!"
            ]
            import random
            return random.choice(responses), True
        else:
            # Generate a new hint for the next round
            next_hint = give_hint(game_object, difficulty=game_object.get('difficulty', 1),
                                  round_num=round_num + 1, previous_hints=previous_hints)

            responses = [
                f"No, that's not it. Here's another hint: {next_hint}",
                f"Good try, but that's not what I'm thinking of. Hint: {next_hint}",
                f"Not quite! Here's a new clue: {next_hint}",
                f"That's not it. Try again! Hint: {next_hint}"
            ]
            import random
            return random.choice(responses), False

    except Exception as e:
        logger.error(f"Error processing guess: {e}")
        return "I'm not sure if that's correct. Let's continue the game.", False
