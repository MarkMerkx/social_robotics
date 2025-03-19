# /api/api_handler.py
import re
import logging
from openai import OpenAI
from .conn import chat_gtp_connection
from .give_hint import give_hint

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
    Uses image reference when available to improve feature accuracy.

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

        # Select candidates based on difficulty
        candidates = []
        for obj_id, obj_data in chatgpt_objects.items():
            obj_name = obj_data.get('name', '').lower()

            # Filter based on difficulty
            if difficulty == 1:  # Easy - common, simple objects
                if any(simple in obj_name for simple in
                       ['chair', 'table', 'bottle', 'cup', 'book', 'desk', 'monitor', 'keyboard']):
                    candidates.append((obj_id, obj_data))
            elif difficulty == 2:  # Medium - moderately complex objects
                if not any(simple in obj_name for simple in ['chair', 'table', 'bottle', 'cup']):
                    candidates.append((obj_id, obj_data))
            else:  # Hard - complex or unusual objects
                if not any(simple in obj_name for simple in
                           ['chair', 'table', 'bottle', 'cup', 'book', 'desk', 'monitor', 'keyboard']):
                    candidates.append((obj_id, obj_data))

        # If no suitable candidates for the difficulty, use all objects
        if not candidates:
            candidates = list(chatgpt_objects.items())

        # Sort candidates by confidence (higher is better)
        candidates.sort(key=lambda x: x[1].get('confidence', 0), reverse=True)

        # Take top 5 candidates or all if less
        top_candidates = dict(candidates[:min(5, len(candidates))])

        # Get the image for the object if available
        has_image = False
        image_base64 = None
        selected_obj_id = None

        # For image-based analysis, select one object with highest confidence
        if candidates:
            selected_obj_id, selected_obj_data = candidates[0]

            # Check if we have annotated image information
            image_path = None
            position_id = selected_obj_data.get('position_id')
            name = selected_obj_data.get('name')

            # Look for an image file that might contain this object
            if position_id and name:
                import glob
                possible_images = glob.glob(f"scan_images/pos_{position_id}*{name}*.jpg")

                if possible_images:
                    image_path = possible_images[0]
                    logger.info(f"Found image for object: {image_path}")

                    # Convert image to base64
                    try:
                        import base64
                        from PIL import Image
                        import io

                        with open(image_path, "rb") as img_file:
                            image_data = img_file.read()
                            image_base64 = base64.b64encode(image_data).decode('utf-8')
                            has_image = True
                    except Exception as e:
                        logger.error(f"Error encoding image: {e}")

        # Prepare the prompt based on whether we have an image
        if has_image:
            # If we have the image, use vision capabilities
            logger.info("Using image-based analysis for object features")

            # Create the message with image and text
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                f"I need to choose an object for an 'I Spy' game based on difficulty level {difficulty} (1=easy, 3=hard). "
                                f"Please analyze the image showing the object '{selected_obj_data.get('name')}' and provide detailed information about it.\n\n"
                                f"For the object in the image, provide the following in a structured JSON format:\n"
                                f"1. 'name': The English name of the object\n"
                                f"2. 'dutch_name': The Dutch translation of the object name\n"
                                f"3. 'confidence': {selected_obj_data.get('confidence', 0.9)}\n"
                                f"4. 'position_id': '{selected_obj_data.get('position_id', '')}'\n"
                                f"5. 'features': A dictionary containing:\n"
                                f"   - 'color': The EXACT color(s) of the object you see in the image\n"
                                f"   - 'size': The approximate size description (small, medium, large)\n"
                                f"   - 'shape': The shape description of the object\n\n"
                                f"IMPORTANT: Base your color description ONLY on what you see in the image. Be precise.\n\n"
                                f"ONLY return the JSON object with this information, no additional text."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}"
                            }
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
            # No image, use text-based approach with enhanced prompting
            logger.info("Using text-based analysis for object selection")

            # Extract some example objects for a more concise prompt
            sample_objects = {}
            for i, (obj_id, obj_data) in enumerate(chatgpt_objects.items()):
                if i < 10:  # Limit to 10 objects to avoid prompt being too large
                    sample_objects[obj_id] = obj_data
                else:
                    break

            # Prepare a structured prompt with examples for better results
            prompt = (
                f"I need to choose an object for an 'I Spy' game based on difficulty level {difficulty} (1=easy, 3=hard). "
                f"Here are some of the detected objects with their positions: {top_candidates}\n\n"
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
                f"   - 'color': The PRIMARY COLOR(s) of the object (be specific - like 'red', 'blue', 'silver', 'wooden', etc.)\n"
                f"   - 'size': The approximate size description (small, medium, large)\n"
                f"   - 'shape': The shape description of the object (like 'rectangular', 'cylindrical', 'square', etc.)\n\n"
                f"IMPORTANT: You MUST provide SPECIFIC values for all features - never use 'unknown'. "
                f"If you're not 100% certain, make your best educated guess based on the object type.\n\n"
                f"Here's an example response for a bottle:\n"
                f"{{\"name\": \"bottle\", \"dutch_name\": \"fles\", \"confidence\": 0.95, \"position_id\": \"2_left\", \"features\": {{\"color\": \"green\", \"size\": \"medium\", \"shape\": \"cylindrical\"}}}}\n\n"
                f"ONLY return the JSON object with this information, no additional text."
            )

            messages = [{"role": "user", "content": prompt}]

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=400,
                temperature=0.3
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

            # Verify that features are not 'unknown'
            features = detailed_object.get('features', {})
            if (features.get('color') == 'unknown' or
                    features.get('size') == 'unknown' or
                    features.get('shape') == 'unknown'):

                # If any feature is unknown, use object name to make educated guesses
                if features.get('color') == 'unknown':
                    # Make an educated guess based on the object name
                    common_colors = {
                        'monitor': 'black', 'computer': 'silver', 'laptop': 'silver',
                        'chair': 'black', 'sofa': 'gray', 'table': 'brown',
                        'book': 'multicolored', 'phone': 'black', 'bottle': 'clear',
                        'mouse': 'black', 'keyboard': 'black', 'cup': 'white',
                        'desk': 'brown', 'window': 'transparent', 'door': 'brown',
                        'wall': 'white', 'floor': 'gray', 'ceiling': 'white'
                    }

                    for key, color in common_colors.items():
                        if key in object_name.lower():
                            features['color'] = color
                            break
                    if features.get('color') == 'unknown':
                        features['color'] = 'multicolored'  # Safe fallback

                if features.get('size') == 'unknown':
                    # Make an educated guess based on the object name
                    large_objects = ['table', 'sofa', 'desk', 'bed', 'bookshelf', 'door', 'window']
                    small_objects = ['phone', 'mouse', 'pen', 'remote', 'key', 'cup', 'bottle']

                    if any(obj in object_name.lower() for obj in large_objects):
                        features['size'] = 'large'
                    elif any(obj in object_name.lower() for obj in small_objects):
                        features['size'] = 'small'
                    else:
                        features['size'] = 'medium'  # Safe fallback

                if features.get('shape') == 'unknown':
                    # Make an educated guess based on the object name
                    shapes = {
                        'monitor': 'rectangular', 'computer': 'rectangular',
                        'chair': 'chair-shaped', 'table': 'rectangular',
                        'book': 'rectangular', 'phone': 'rectangular',
                        'bottle': 'cylindrical', 'cup': 'cylindrical',
                        'ball': 'spherical', 'bowl': 'round'
                    }

                    for key, shape in shapes.items():
                        if key in object_name.lower():
                            features['shape'] = shape
                            break
                    if features.get('shape') == 'unknown':
                        features['shape'] = 'irregular'  # Safe fallback

                detailed_object['features'] = features

            # Add information if image was used for feature detection
            detailed_object['features_from_image'] = has_image

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
