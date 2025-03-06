import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_2.gesture_control.say_animated import say_animated

logger = logging.getLogger(__name__)


@inlineCallbacks
def wait_for_response(prompt_text, session, stt, timeout=15):
    """
    Waits for an STT response from the user.
    If prompt_text is provided, the robot will speak it; if None, no dialogue is spoken.
    It resets the STT words list and then polls for a response.

    :param prompt_text: Optional text to speak before waiting for a response.
    :param session: The WAMP session (for dialogue actions).
    :param stt: The shared SpeechToText instance.
    :param timeout: Maximum seconds to wait.
    :return: The recognized user response as a string (or None on timeout).
    """
    if prompt_text:
        logger.debug("Prompting user: %s", prompt_text)
        stt.words = []  # clear previous words
        # yield session.call("rie.dialogue.say", text=prompt_text)
        yield say_animated(session, prompt_text, gesture_name="beat_gesture")
        yield sleep(1.5)
        stt.words = []
    else:
        # If no prompt_text, simply clear any previous words.
        stt.words = []

    response = None
    waited = 0.0
    poll_interval = 1.0
    while not response and waited < timeout:
        yield sleep(poll_interval)
        waited += poll_interval
        words = stt.give_me_words()  # clears new_words flag.
        if words:
            raw_response = " ".join(words)
            # Remove all "<" and ">" characters which are used in the prompts
            cleaned = raw_response.replace("<", "").replace(">", "").strip()
            # If the cleaned response is very long, take only the first word.
            if len(cleaned) > 50:
                cleaned = cleaned.split()[0]
            response = cleaned
            logger.debug("Received STT response: %s", response)
        else:
            logger.debug("Waiting for STT response... (%.1f/%d sec)", waited, timeout)
    if not response:
        logger.debug("Timeout reached with no response.")
    return response
