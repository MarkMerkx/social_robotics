import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from game_utils import wait_for_response
from api.api_handler import answer_question_with_api, generate_secret_word

logger = logging.getLogger(__name__)


@inlineCallbacks
def play_game_user_guesses(session, stt):
    """
    Game mode where the robot chooses a word (via ChatGPT) and the user asks yes/no questions.
    Every input is treated as a question; if the secret word appears in the input,
    the game ends with a win.
    """
    logger.debug("Starting play_game_user_guesses()")
    # Generate a secret word using ChatGPT.
    chosen_word = generate_secret_word()
    logger.debug("Robot's chosen word (generated via ChatGPT): %s", chosen_word)

    yield session.call("rie.dialogue.say", text="I have chosen a word. Ask me yes/no questions to narrow it down.")
    yield sleep(1.5)

    max_rounds = 15
    round_counter = 0
    while round_counter < max_rounds:
        # Use None as the prompt_text to skip re-speaking a prompt.
        user_input = yield wait_for_response(None, session, stt, timeout=20)
        if not user_input:
            yield session.call("rie.dialogue.say", text="I didn't catch that. Please try again.")
            continue
        logger.debug("User input: %s", user_input)
        # If the user input mentions the secret word, congratulate and end.
        if chosen_word.lower() in user_input.lower():
            yield session.call("rie.dialogue.say", text="Congratulations! You guessed it!")
            logger.debug("User mentioned the secret word. Ending game.")
            break
        else:
            # Use the API to answer the user's yes/no question.
            answer = answer_question_with_api(chosen_word, user_input)
            logger.debug("Answer from API: %s", answer)
            yield session.call("rie.dialogue.say", text=answer)
            round_counter += 1

    if round_counter >= max_rounds:
        yield session.call("rie.dialogue.say", text=f"Sorry, you've run out of rounds. The word was {chosen_word}.")
        logger.debug("User failed to guess the word within max rounds.")

    yield session.call("rie.dialogue.say", text="Thanks for playing!")
    logger.debug("Game ended.")
