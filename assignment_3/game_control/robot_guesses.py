import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_3.gesture_control.scanning import run_scan
from assignment_3.api.api_handler import choose_object

logger = logging.getLogger(__name__)

def robot_guess(detected_objects, hints):
    """
    Generates a guess for the object based on detected objects and hints provided.
    """
    possible_objects = [obj for obj in detected_objects if all(hint in obj['features'] for hint in hints)]
    if not possible_objects:
        return "I can’t find any object that matches your hints."
    import random
    guess = random.choice(possible_objects)
    return f"Is it a {guess['dutch_name']} or {guess['name']}?"

@inlineCallbacks
def play_game_robot_guesses(session, stt, dialogue_manager, difficulty=1, scan_mode="static"):
    """
    I Spy game where the robot guesses the object the user has chosen.

    :param session: WAMP session for controlling the robot
    :type session: object
    :param stt: SpeechToText instance for listening to user responses
    :type stt: object
    :param dialogue_manager: DialogueManager instance for speaking and listening
    :type dialogue_manager: DialogueManager
    :param difficulty: Difficulty level (1=easy, 2=medium, 3=hard), defaults to 1
    :type difficulty: int, optional
    :param scan_mode: Scan mode for the robot ("static" or "360"), defaults to "static"
    :type scan_mode: str, optional

    The game proceeds as follows:
    1. The user thinks of an object, and the robot asks for an initial hint (color).
    2. The robot scans the room and makes guesses based on the hints provided.
    3. The user gives feedback ("yes" or "no"), and the robot asks for more hints if needed.
    4. The game continues until the robot guesses correctly or reaches the maximum number of guesses.

    .. note:: The difficulty parameter is currently not used in this game mode.
    """
    # Step 1: Object selection
    yield dialogue_manager.say("Please look around the room and think of an object.", gesture="beat_gesture")
    yield sleep(5)
    confirmation = yield dialogue_manager.ask_with_reprompt(
        "Have you chosen an object?", gesture="beat_gesture", timeout=20
    )
    if not confirmation or "yes" not in confirmation.lower():
        yield dialogue_manager.say("Okay, I’ll give you more time next round!", gesture="goodbye_wave")
        return

    # Step 2: Initial hint
    initial_hint_prompt = "<nl>Kun je me de kleur van je object vertellen?</nl> Can you tell me the color of your object?"
    initial_hint = yield dialogue_manager.ask_with_reprompt(initial_hint_prompt, gesture="beat_gesture", timeout=20)
    if not initial_hint:
        yield dialogue_manager.say("I didn’t catch that. Let’s assume it’s red for now.", gesture="shake_no")
        initial_hint = "red"
    hints = [initial_hint]

    # Step 3: Scan and guess loop
    yield dialogue_manager.say("Now I’ll scan the room to find your object!", gesture="beat_gesture")
    scan_results, detected_objects = yield run_scan(session, mode=scan_mode)

    max_guesses = 5
    guess_count = 0
    while guess_count < max_guesses:
        guess = robot_guess(detected_objects, hints)
        yield dialogue_manager.say(guess, gesture="beat_gesture")
        feedback = yield dialogue_manager.listen(timeout=20)

        if feedback and "yes" in feedback.lower():
            yield dialogue_manager.say("Yay! I got it right!", gesture="celebration")
            break
        else:
            guess_count += 1
            if guess_count < max_guesses:
                additional_prompt = "<nl>Kun je me nog een hint geven?</nl> Can you give me another hint?"
                yield dialogue_manager.say(additional_prompt, gesture="beat_gesture")
                additional_hint = yield dialogue_manager.listen(timeout=20)
                if additional_hint:
                    hints.append(additional_hint)
                else:
                    yield dialogue_manager.say("No hint? I’ll try again anyway!", gesture="beat_gesture")

    # Step 5: End game
    if guess_count >= max_guesses:
        yield dialogue_manager.say("I give up! Your object was too tricky for me.", gesture="defeat")
    yield dialogue_manager.say("Thanks for playing with me!", gesture="goodbye_wave")