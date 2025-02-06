from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from api.guess_call import guess
from alpha_mini_rug.speech_to_text import SpeechToText

# Initialize the SpeechToText instance
stt = SpeechToText()


@inlineCallbacks
def wait_for_response(prompt_text, session, timeout=15):
    """
    Instructs the robot to speak a prompt and waits for a response using STT.

    :param prompt_text: The text to be spoken.
    :param session: The WAMP session for calling dialogue actions.
    :param timeout: Maximum seconds to wait for a response.
    :return: The recognized user response (as a string) or None.
    """
    yield session.call("rie.dialogue.say", text=prompt_text)
    response = None
    waited = 0
    while not response and waited < timeout:
        yield sleep(1)
        words = stt.give_me_words()
        if words:
            response = " ".join(words)
        waited += 1
    return response


@inlineCallbacks
def play_game(session):
    """
    Implements the overall game flow:
      1. Ask if the user wants to play.
      2. Instruct the user to think of a word.
      3. Wait until the user confirms readiness.
      4. Enter a round-based loop where the robot makes guesses until the word is found.
    """
    previous_guesses = []  # List of dictionaries: {"guess": <question>, "feedback": <user response>}

    # Step 1: Ask if the user wants to play
    user_response = yield wait_for_response("Do you want to play a game? Please say Yes or No.", session)
    if not user_response or "no" in user_response.lower():
        yield session.call("rie.dialogue.say", text="Okay, maybe next time!")
        return

    # Step 2: Ask user to think of a word
    yield session.call("rie.dialogue.say", text="Great! Please think of a word and keep it in your mind.")
    yield sleep(5)

    # Step 3: Wait for user readiness
    ready = None
    while not ready or "yes" not in ready.lower():
        ready = yield wait_for_response("Are you ready? Please say Yes when you are.", session)
        if not ready or "yes" not in ready.lower():
            yield session.call("rie.dialogue.say", text="Okay, waiting until you're ready...")
            yield sleep(3)

    yield session.call("rie.dialogue.say", text="Let's start!")
    last_feedback = ""
    max_rounds = 10
    round_counter = 0

    while round_counter < max_rounds:
        # Generate the next yes/no question using ChatGPT via guess_call
        guess_question = guess(last_feedback, previous_guesses)
        yield session.call("rie.dialogue.say", text=guess_question)

        # Wait for the user's answer to the question
        feedback = yield wait_for_response("Please answer the question.", session)
        if not feedback:
            feedback = "No response"

        # Store this round's guess and feedback
        previous_guesses.append({'guess': guess_question, 'feedback': feedback})
        round_counter += 1

        # Check if the feedback indicates that the guess is correct
        if any(affirm in feedback.lower() for affirm in ["correct", "yes, that's it", "exactly"]):
            yield session.call("rie.dialogue.say", text="Yay! I guessed it!")
            break
        else:
            last_feedback = feedback

    if round_counter >= max_rounds:
        yield session.call("rie.dialogue.say", text="I give up! That was a challenging word.")
    yield session.call("rie.dialogue.say", text="Thanks for playing!")