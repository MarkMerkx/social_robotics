import logging
import re
import string
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from api.api_handler import guess
from game_utils import wait_for_response

logger = logging.getLogger(__name__)


@inlineCallbacks
def play_game_robot_guesses(session, stt):
    """
    Game mode where the user thinks of a word and the robot tries to guess it by asking yes/no questions.
    """
    logger.debug("Starting play_game_robot_guesses()")
    previous_guesses = []  # Each entry: {'guess': <question>, 'feedback': <user response>}

    yield session.call("rie.dialogue.say", text="Great! Please think of a word and keep it in your mind.")
    logger.debug("User instructed to think of a word.")
    yield sleep(5)

    # Wait for user readiness.
    ready = None
    while not ready or "yes" not in ready.lower():
        ready = yield wait_for_response("Are you ready? Please say Yes when you are.", session, stt, timeout=20)
        logger.debug("User readiness response: %s", ready)
        if not ready or "yes" not in ready.lower():
            yield session.call("rie.dialogue.say", text="Okay, waiting until you're ready...")
            logger.debug("User not ready; waiting 3 seconds before trying again.")
            yield sleep(3)

    yield session.call("rie.dialogue.say", text="Let's start!")
    logger.debug("User confirmed readiness. Starting guessing rounds.")
    last_feedback = ""
    max_rounds = 15
    round_counter = 0

    while round_counter < max_rounds:
        logger.debug("Round %d starting...", round_counter + 1)
        # Generate the next question using ChatGPT.
        guess_question = guess(last_feedback, previous_guesses)
        # Remove all '<' and '>' characters from the prompts
        clean_guess = re.sub(r'[<>]', '', guess_question).strip()
        logger.debug("Generated guess question: %s", clean_guess)

        # Robot speaks the question.
        yield session.call("rie.dialogue.say", text=clean_guess)
        yield sleep(3)

        # Wait for the user's answer.
        feedback = yield wait_for_response(None, session, stt)
        if not feedback:
            feedback = "No response"
            logger.debug("No feedback received; defaulting to: %s", feedback)
        else:
            logger.debug("Feedback received: %s", feedback)

        previous_guesses.append({'guess': clean_guess, 'feedback': feedback})
        round_counter += 1

        # Clean feedback (remove punctuation) for a robust match.
        feedback_cleaned = feedback.lower().translate(str.maketrans("", "", string.punctuation))
        win_keywords = ["correct", "yes thats it", "exactly", "yes you guessed it"]
        if any(affirm in feedback_cleaned for affirm in win_keywords):
            yield session.call("rie.dialogue.say", text="Yay! I guessed it!")
            logger.debug("User confirmed correct guess. Ending game.")
            break
        else:
            last_feedback = feedback
            logger.debug("Continuing game with last feedback: %s", last_feedback)

    if round_counter >= max_rounds:
        yield session.call("rie.dialogue.say", text="I give up! That was a challenging word.")
        logger.debug("Reached maximum rounds; game over.")

    yield session.call("rie.dialogue.say", text="Thanks for playing!")
    logger.debug("Game ended. Thank you for playing!")
