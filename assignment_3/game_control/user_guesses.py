import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep

from .game_utils import wait_for_response
from ..api.api_handler import answer_question_with_api, generate_secret_word
from assignment_2.gesture_control.say_animated import say_animated


@inlineCallbacks
def play_game_user_guesses(session, stt):
    logger = logging.getLogger(__name__)
    chosen_word = generate_secret_word()
    logger.debug("Robot's chosen word: %s", chosen_word)

    # Use a "beat_gesture" for normal/neutral speech:
    yield say_animated(session, "I have chosen a word. Ask me yes/no questions to narrow it down.", gesture_name="beat_gesture")
    yield sleep(1.5)

    max_rounds = 15
    round_counter = 0

    while round_counter < max_rounds:
        user_input = yield wait_for_response(None, session, stt, timeout=20)
        if not user_input:
            # Use a "shake_no" gesture to show we didn't catch that
            yield say_animated(session, "I didn't catch that. Please try again.", gesture_name="shake_no")
            continue

        logger.debug("User input: %s", user_input)

        # Check if user guessed the secret word:
        if chosen_word.lower() in user_input.lower():
            # Celebrate if the user is correct
            yield say_animated(session, "Congratulations! You guessed it!", gesture_name="celebration")
            break
        else:
            # Let the API produce a yes/no style answer:
            answer = answer_question_with_api(chosen_word, user_input)
            logger.debug("Answer from API: %s", answer)

            # Decide on nod/shake for yes or no
            if "yes" in answer.lower():
                gesture = "nod_yes"
            elif "no" in answer.lower():
                gesture = "shake_no"
            else:
                # If the answer is more neutral or unclear, maybe just do a beat gesture
                gesture = "beat_gesture"

            yield say_animated(session, answer, gesture_name=gesture)
            round_counter += 1

    if round_counter >= max_rounds:
        # If user never guessed, do a "sad" or "shake_no" gesture:
        yield say_animated(session, f"Sorry, you've run out of rounds. The word was {chosen_word}.", gesture_name="shake_no")

    # End of game message (neutral beat)
    yield say_animated(session, "Thanks for playing!", gesture_name="beat_gesture")
