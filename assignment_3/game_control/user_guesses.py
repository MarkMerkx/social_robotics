import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_3.gesture_control.scanning import run_scan
from assignment_3.api.api_handler import choose_object, start_i_spy_game, process_guess
from assignment_3.gesture_control.point_to_object import point_to_object

logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game_user_guesses(session, stt, dialogue_manager, difficulty=1, scan_mode="static"):
    """
    I Spy game where the user guesses the object the robot has chosen.

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
    1. The robot scans the room and chooses an object based on the difficulty.
    2. The robot gives an initial hint.
    3. The user guesses the object, with the robot providing feedback and additional hints.
    4. If the user struggles (after 3 incorrect guesses), the difficulty is lowered (if above 1).
    5. The game continues until the user guesses correctly or reaches the maximum number of rounds.

    .. note:: The difficulty will not go below 1, even if dynamically adjusted.
    """
    logger.debug("Starting I Spy user-guesses game...")

    yield session.call("rom.optional.behavior.play", name="BlocklyStand")
    yield dialogue_manager.say("Let me look around for something interesting...", gesture="beat_gesture")
    scan_results, detected_objects = yield run_scan(session, mode=scan_mode)

    chosen_object = choose_object(detected_objects, difficulty)
    if not chosen_object:
        yield dialogue_manager.say("I couldn't find anything interesting. Sorry!", gesture="shake_no")
        return

    intro, initial_hint = start_i_spy_game(chosen_object, difficulty)
    yield dialogue_manager.say(intro, gesture="beat_gesture")
    yield dialogue_manager.say(initial_hint, gesture="beat_gesture")

    round_num = 0
    max_rounds = 8
    previous_hints = [initial_hint]
    while round_num < max_rounds:
        game_context = {
            'game_object': chosen_object,
            'difficulty': difficulty,
            'round_num': round_num,
            'previous_hints': previous_hints
        }
        guess = yield dialogue_manager.ask_with_reprompt(
            "What do you think the object is?", gesture="beat_gesture", game_context=game_context, timeout=12
        )
        if not guess:
            yield dialogue_manager.say("I didn’t catch that. Let’s try again!", gesture="shake_no")
            continue

        response_text, is_correct = process_guess(guess, chosen_object, round_num, previous_hints)
        yield dialogue_manager.say(response_text, gesture="beat_gesture")
        if is_correct:
            yield dialogue_manager.say(f"Here it is!", gesture="beat_gesture")
            yield point_to_object(session, chosen_object)
            yield sleep(3)
            break
        else:
            # Lower difficulty after 3 incorrect guesses (round_num >= 2 since it starts at 0)
            if round_num >= 2 and difficulty > 1:
                difficulty -= 1
                yield dialogue_manager.say("This seems tricky! I'll make the hints a bit easier.", gesture="beat_gesture")
            previous_hints.append(response_text)
            round_num += 1

    if round_num >= max_rounds:
        object_name = chosen_object.get('name', 'it')
        yield dialogue_manager.say(f"You’re out of guesses. It was {object_name}.", gesture="shake_no")

    yield dialogue_manager.say("Thanks for playing I Spy with me!", gesture="goodbye_wave")
    logger.debug("I Spy user-guesses flow ended.")