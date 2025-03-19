# /game_control/play_game.py
import logging

from twisted.internet.defer import inlineCallbacks

from assignment_3.game_control.game_utils import wait_for_response
# We import the i-spy style user_guesses function (repurposed below)
from assignment_3.game_control.user_guesses import play_game_user_guesses

logging.basicConfig(
    format='%(asctime)s GAME HANDLER %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game(session, stt):
    """
    Main entry point for the game:
      - Asks user if they want to play
      - If yes, calls 'play_game_user_guesses' (our new I Spy flow)
      - If no, ends
    """
    playing = True
    while playing:
        # 1. Ask user if they want to play
        user_response = yield wait_for_response(
            "Do you want to play a game? Please say Yes or No.",
            session, stt
        )
        logger.debug(f"User response to invitation: {user_response}")
        if not user_response or "no" in user_response.lower():
            yield session.call("rie.dialogue.say", text="Okay, maybe next time!")
            logger.debug("User declined to play.")
            playing = False
            break

        # 2. Actually play the new i-spy flow
        logger.debug("Starting new I Spy game (user guesses).")
        yield play_game_user_guesses(session, stt)

        # 3. After game ends, ask if user wants to play again
        again = yield wait_for_response(
            "Do you want to play again? Please say Yes or No.",
            session, stt
        )
        if again and "yes" in again.lower():
            playing = True
        else:
            playing = False
            yield session.call("rie.dialogue.say", text="Okay, thanks for playing!")
            logger.debug("User chose to end the session.")
            yield session.leave()  # Terminate the session.
