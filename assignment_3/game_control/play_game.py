import logging
from twisted.internet.defer import inlineCallbacks
from assignment_3.dialogue.dialogue_manager import DialogueManager
from assignment_3.game_control.user_guesses import play_game_user_guesses
from assignment_3.game_control.robot_guesses import play_game_robot_guesses
from autobahn.twisted.util import sleep

logging.basicConfig(
    format='%(asctime)s GAME HANDLER %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S')
logger = logging.getLogger(__name__)

@inlineCallbacks
def play_game(session, stt, scan_mode="static"):
    """
    Main entry point for the game, handling greeting and game mode selection.

    :param session: WAMP session for controlling the robot
    :type session: object
    :param stt: SpeechToText instance for listening to user responses
    :type stt: object
    :param scan_mode: Scan mode for the robot ("static" or "360"), defaults to "static"
    :type scan_mode: str, optional

    The game flow is as follows:
    1. The robot greets the user and asks for their name.
    2. The robot asks if the user wants to play a game.
    3. If yes, the robot asks which game mode to play ("I guess" or "You guess").
    4. Based on the user's choice, the corresponding game mode is played.
    5. After the game, the robot asks if the user wants to play again.

    .. note:: Difficulty selection is currently commented out and defaults to 1.
    """
    dialogue_manager = DialogueManager(session, stt)
    playing = True

    # Greeting: Ask for the child's name
    yield dialogue_manager.say("Hello! What's your name?", gesture="beat_gesture")
    yield sleep(2)
    user_name_response = yield dialogue_manager.listen(timeout=8)
    user_name = user_name_response.strip().split()[-1] if user_name_response else "friend"
    yield dialogue_manager.say(f"Nice to meet you, {user_name}!", gesture="goodbye_wave")

    while playing:
        # Ask if the user wants to play
        yield dialogue_manager.say("Do you want to play a game, " + user_name + "? Please say Yes or No.", gesture="beat_gesture")
        response = yield dialogue_manager.listen(timeout=10)
        if not response or "no" in response.lower():
            yield dialogue_manager.say("Okay, maybe next time!", gesture="shake_no")
            playing = False
            break

        # Ask for difficulty (commented out for now)
        # yield dialogue_manager.say("Do you want an easy, medium, or hard game?", gesture="beat_gesture")
        # difficulty_response = yield dialogue_manager.listen(timeout=10)
        # if difficulty_response:
        #     difficulty_response = difficulty_response.lower()
        #     if "easy" in difficulty_response:
        #         difficulty = 1
        #     elif "medium" in difficulty_response:
        #         difficulty = 2
        #     elif "hard" in difficulty_response:
        #         difficulty = 3
        #     else:
        #         difficulty = 1  # default to easy if unclear
        # else:
        #     difficulty = 1  # default to easy if no response
        difficulty = 1  # Default difficulty

        # Ask which game mode to play
        yield dialogue_manager.say(
            f"Great, {user_name}! Do you want to guess the object or should I search for the object? Say 'I guess' or 'You guess'.",
            gesture="beat_gesture"
        )
        choice = yield dialogue_manager.listen(timeout=10)
        if choice and "i guess" in choice.lower():
            logger.debug("User chose 'I guess' mode.")
            yield play_game_user_guesses(session, stt, dialogue_manager, difficulty=difficulty, scan_mode=scan_mode)
        elif choice and "you guess" in choice.lower():
            logger.debug("User chose 'You guess' mode.")
            yield play_game_robot_guesses(session, stt, dialogue_manager, difficulty=difficulty, scan_mode=scan_mode)
        else:
            yield dialogue_manager.say("I didn't understand. Let's play where you guess the object.", gesture="shake_no")
            yield play_game_user_guesses(session, stt, dialogue_manager, difficulty=difficulty, scan_mode=scan_mode)

        # Ask to play again
        yield dialogue_manager.say("Do you want to play again, " + user_name + "? Please say Yes or No.", gesture="beat_gesture")
        again = yield dialogue_manager.listen(timeout=10)
        if again and "yes" in again.lower():
            playing = True
        else:
            playing = False
            yield dialogue_manager.say(f"Okay, thanks for playing, {user_name}!", gesture="goodbye_wave")
            yield session.leave()