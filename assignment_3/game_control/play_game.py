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
def play_game(session, stt):
    """Main entry point for the game, handling greeting and game mode selection."""
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

        # Ask which game mode to play
        yield dialogue_manager.say(
            f"Great, {user_name}! Do you want to guess the object or should I search for the object? Say 'I guess' or 'You guess'.",
            gesture="beat_gesture"
        )
        choice = yield dialogue_manager.listen(timeout=10)
        if choice and "i guess" in choice.lower():
            logger.debug("User chose 'I guess' mode.")
            yield play_game_user_guesses(session, stt, dialogue_manager)
        elif choice and "you guess" in choice.lower():
            logger.debug("User chose 'You guess' mode.")
            yield play_game_robot_guesses(session, stt, dialogue_manager)
        else:
            yield dialogue_manager.say("I didn't understand. Let's play where you guess the object.", gesture="shake_no")
            yield play_game_user_guesses(session, stt, dialogue_manager)

        # Ask to play again
        yield dialogue_manager.say("Do you want to play again, " + user_name + "? Please say Yes or No.", gesture="beat_gesture")
        again = yield dialogue_manager.listen(timeout=10)
        if again and "yes" in again.lower():
            playing = True
        else:
            playing = False
            yield dialogue_manager.say(f"Okay, thanks for playing, {user_name}!", gesture="goodbye_wave")
            yield session.leave()