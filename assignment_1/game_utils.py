import logging
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep

logger = logging.getLogger(__name__)


@inlineCallbacks
def wait_for_response(prompt_text, session, stt, timeout=15):
    """
    Instructs the robot to speak a prompt and then waits for an STT response.
    It clears any prior STT words by resetting the STT’s words list,
    waits briefly for the robot's own speech to finish, then polls for user speech.

    :param prompt_text: The text to be spoken.
    :param session: The WAMP session (for dialogue actions).
    :param stt: The shared SpeechToText instance.
    :param timeout: Maximum seconds to wait for a response.
    :return: The recognized user response as a string (or None on timeout).
    """
    logger.debug("Prompting user: %s", prompt_text)

    # Clear previous words.
    stt.words = []

    yield session.call("rie.dialogue.say", text=prompt_text)

    # Wait for the robot's own speech to finish.
    yield sleep(1.5)
    stt.words = []

    response = None
    waited = 0.0
    poll_interval = 1.0  # poll every second
    while not response and waited < timeout:
        yield sleep(poll_interval)
        waited += poll_interval
        words = stt.give_me_words()  # this call clears the new_words flag.
        if words:
            raw_response = " ".join(words)
            cleaned = raw_response.replace("<<<", "").replace(">>>", "").strip()
            if len(cleaned) > 50:
                cleaned = cleaned.split()[0]
            response = cleaned
            logger.debug("Received STT response: %s", response)
        else:
            logger.debug("Waiting for STT response... (%.1f/%d sec)", waited, timeout)

    if not response:
        logger.debug("Timeout reached with no response.")
    return response
