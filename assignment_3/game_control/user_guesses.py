import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_3.gesture_control.scanning import run_scan, MODE_STATIC
from assignment_3.api.api_handler import choose_object, start_i_spy_game, process_guess
from assignment_3.gesture_control.point_to_object import point_to_object

logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game_user_guesses(session, stt, dialogue_manager):
    """I Spy game where the user guesses the object the robot has chosen."""
    logger.debug("Starting I Spy user-guesses game...")

    yield session.call("rom.optional.behavior.play", name="BlocklyStand")
    yield dialogue_manager.say("Let me look around for something interesting...", gesture="beat_gesture")
    scan_results, detected_objects = yield run_scan(session, mode=MODE_STATIC)

    difficulty = 1
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
            previous_hints.append(response_text)
            round_num += 1

    if round_num >= max_rounds:
        object_name = chosen_object.get('name', 'it')
        yield dialogue_manager.say(f"You’re out of guesses. It was {object_name}.", gesture="shake_no")

    yield dialogue_manager.say("Thanks for playing I Spy with me!", gesture="goodbye_wave")
    logger.debug("I Spy user-guesses flow ended.")