import logging
import random
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from game_utils import wait_for_response
from api.answer_question import answer_question_with_api

logger = logging.getLogger(__name__)


@inlineCallbacks
def play_game_user_guesses(session, stt):
    """
    Game mode where the robot chooses a word and the user asks yes/no questions
    to narrow it down, or submits a final guess.
    The secret word is chosen from a list (or could be generated dynamically).
    ChatGPT is used to determine if a user question is relevant.
    """
    logger.debug("Starting play_game_user_guesses()")
    words = ["apple", "banana", "orange", "grape", "pineapple", "strawberry"]
    # Alternatively, you could have ChatGPT choose a word.
    chosen_word = random.choice(words)
    logger.debug("Robot's chosen word: %s", chosen_word)

    yield session.call("rie.dialogue.say", text="I have chosen a word. "
                                                "You may ask yes/no questions to narrow it down, "
                                                "or say 'I guess' followed by your guess.")
    yield sleep(1.5)

    max_rounds = 10
    round_counter = 0
    while round_counter < max_rounds:
        prompt = f"Round {round_counter + 1}: What is your question or guess?"
        user_input = yield wait_for_response(prompt, session, stt, timeout=20)
        if not user_input:
            yield session.call("rie.dialogue.say", text="I didn't catch that. Please try again.")
            continue
        logger.debug("User input: %s", user_input)
        # If the user input starts with "I guess", treat it as a final guess.
        if user_input.lower().startswith("i guess"):
            guess_word = user_input[7:].strip()  # Remove "I guess"
            logger.debug("User final guess: %s", guess_word)
            if chosen_word.lower() in guess_word.lower() or guess_word.lower() in chosen_word.lower():
                yield session.call("rie.dialogue.say", text="Congratulations! You guessed it!")
                logger.debug("User guessed correctly. Ending game.")
                break
            else:
                yield session.call("rie.dialogue.say",
                                   text="That's not it. Please continue asking questions or try another guess.")
                round_counter += 1
        else:
            # Use ChatGPT to answer the user's yes/no question about the secret word.
            answer = answer_question_with_api(chosen_word, user_input)
            yield session.call("rie.dialogue.say", text=answer)
            round_counter += 1

    if round_counter >= max_rounds:
        yield session.call("rie.dialogue.say", text=f"Sorry, you've run out of rounds. The word was {chosen_word}.")
        logger.debug("User failed to guess the word within max rounds.")

    yield session.call("rie.dialogue.say", text="Thanks for playing!")
    logger.debug("Game ended.")
