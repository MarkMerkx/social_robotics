# /game_control/user_guesses.py
import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_3.game_control.game_utils import wait_for_response
from assignment_3.gesture_control.say_animated import say_animated

# Import scanning, object selection, guessing logic for I Spy
from assignment_3.gesture_control.scanning import perform_scan, MODE_STATIC
from assignment_3.api.api_handler import choose_object, start_i_spy_game, process_guess
from assignment_3.gesture_control.point_to_object import point_to_object  # your new pointer logic

logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game_user_guesses(session, stt):
    """
    New I Spy flow (overwrites old user-guesses code).
    The user will guess the object that the robot scanned.
    1) Robot stands, track face, wave, greet user by name
    2) Perform scanning
    3) Choose object
    4) start_i_spy_game => returns intro + initial hint
    5) loop collecting guesses with process_guess
    6) If correct, point to object
    """
    logger.debug("Starting I Spy user-guesses game...")

    # 1) Robot stands up, starts face tracking, greet user
    yield session.call("rom.optional.behavior.play", name="BlocklyStand")
    yield session.call("rie.vision.face.find")
    yield session.call("rie.vision.face.track")

    # Ask user's name
    yield say_animated(session, "Hello! What's your name?", gesture_name="beat_gesture")
    user_name_response = yield wait_for_response(None, session, stt, timeout=8)
    if not user_name_response:
        user_name = "friend"
    else:
        user_name = user_name_response.strip().split()[-1]  # naive approach

    say_animated(session, f"Nice to meet you, {user_name}!", gesture_name="beat_gesture")
    yield session.call("rom.optional.behavior.play",
                       name="BlocklyWaveRightArm")

    # 2) Perform a static scan to detect objects
    yield say_animated(session, "Let me look around for something interesting...", gesture_name="beat_gesture")
    scan_results, all_objects = yield perform_scan(session, mode=MODE_STATIC)

    # 3) Choose an object to play with, difficulty=1 for easy
    difficulty = 1
    chosen_object = choose_object(all_objects, difficulty)
    if not chosen_object:
        yield say_animated(session, "I couldn't find anything interesting. Sorry!", gesture_name="shake_no")
        return

    # 4) Start the I Spy game => get intro + initial hint
    intro, initial_hint = start_i_spy_game(chosen_object, difficulty)
    yield say_animated(session, intro, gesture_name="beat_gesture")
    yield say_animated(session, initial_hint, gesture_name="beat_gesture")

    # We'll store hints or responses so we can pass them to process_guess
    round_num = 0
    max_rounds = 8
    previous_hints = [initial_hint]

    while round_num < max_rounds:
        user_guess = yield wait_for_response("What do you think the object is?", session, stt, timeout=12)
        if not user_guess:
            yield say_animated(session, "I'm sorry, I didn't catch that. Could you repeat?", gesture_name="shake_no")
            continue

        # 5) Use process_guess to see if it's correct
        response_text, is_correct = process_guess(user_guess, chosen_object, round_num, previous_hints)
        yield say_animated(session, response_text, gesture_name="beat_gesture")

        if is_correct:
            # If correct, robot points to the object physically
            yield say_animated(session, f"Here it is, {user_name}!", gesture_name="beat_gesture")
            yield point_to_object(session, chosen_object)
            break
        else:
            previous_hints.append(response_text)
            round_num += 1

    if round_num >= max_rounds:
        # If they never guessed
        object_name = chosen_object.get('name', 'it')
        yield say_animated(session, f"You're out of guesses. The object was {object_name}.", gesture_name="shake_no")

    # End
    yield say_animated(session, "Thanks for playing I Spy with me!", gesture_name="wave_gesture")

    # Optionally stop face tracking
    yield session.call("rie.vision.face.trackstop")
    yield session.call("rie.vision.face.findstop")

    logger.debug("I Spy user-guesses flow ended.")
