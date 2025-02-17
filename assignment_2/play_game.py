import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from robot_guesses import play_game_robot_guesses
from user_guesses import play_game_user_guesses
from game_utils import wait_for_response
from say_animated import say_animated

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game(session, stt):
    """
    Main game entry point.
    Ask if the user wants to play, choose the mode, and after the game ends ask if the user wants to play again.
    If the user declines, the session is left.
    """
    playing = True
    while playing:
        logger.debug("Starting new game...")
        # Invite the user to play.
        user_response = yield wait_for_response("Do you want to play a game? Please say Yes or No.", session, stt)
        logger.debug("User response to invitation: %s", user_response)
        if not user_response or "no" in user_response.lower():
            yield session.call("rie.dialogue.say", text="Okay, maybe next time!")
            logger.debug("User declined to play.")
            playing = False
            break

        # Ask which mode they want.
        yield say_animated(session,
                           "Great! Would you like me to guess your word, or would you like to guess my word? "
                                "Please say 'I guess' if you want to guess my word, or 'You guess' if you want me to guess yours.", gesture_name="beat_gesture")
        mode_response = yield wait_for_response("Please choose the game mode.", session, stt, timeout=20)
        logger.debug("Mode selection response: %s", mode_response)

        if mode_response and "i guess" in mode_response.lower():
            mode = "user_guesses"
        elif mode_response and "you guess" in mode_response.lower():
            mode = "robot_guesses"
        else:
            mode = "robot_guesses"

        if mode == "robot_guesses":
            yield play_game_robot_guesses(session, stt)
        else:
            yield play_game_user_guesses(session, stt)

        # After the game ends, ask if the user wants to play again.
        again = yield wait_for_response("Do you want to play another game? Please say Yes or No.", session, stt)
        if again and "yes" in again.lower():
            playing = True
        else:
            playing = False
            yield session.call("rie.dialogue.say", text="Okay, thanks for playing!")
            logger.debug("User chose to end the session.")
            yield session.leave()  # Terminate the session.
