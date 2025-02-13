import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from api.guess_call import guess  # used in robot_guesses mode
from robot_guesses import play_game_robot_guesses
from user_guesses import play_game_user_guesses
from game_utils import wait_for_response  # import from game_utils

logging.basicConfig(
    format='%(asctime)s %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)


@inlineCallbacks
def play_game(session, stt):
    """
    Main game entry point.
    First, ask if the user wants to play. Then, ask which mode:
      - "Robot guesses": The robot guesses the user's word.
      - "User guesses": (I guess mode) The robot picks a word and the user asks questions and makes a guess.
    """
    logger.debug("Starting play_game()")

    # Invite the user to play.
    user_response = yield wait_for_response("Do you want to play a game? Please say Yes or No.", session, stt)
    logger.debug("User response to invitation: %s", user_response)
    if not user_response or "no" in user_response.lower():
        yield session.call("rie.dialogue.say", text="Okay, maybe next time!")
        logger.debug("User declined to play.")
        return

    # Ask which mode they want.
    yield session.call("rie.dialogue.say",
                       text="Great! Would you like me to guess your word, or would you like to guess my word? "
                            "Please say 'I guess' if you want to guess my word, or 'You guess' if you want me to guess yours.")
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
