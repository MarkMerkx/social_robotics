from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.component import Component, run
from autobahn.twisted.util import sleep
import logging
from assignment_3.dialogue.dialogue_manager import DialogueManager


# Dummy STT class for testing
class DummySTT:
    def __init__(self):
        self.words = []

    def give_me_words(self):
        # Simulate a response
        if not self.words:
            return []
        words = self.words
        self.words = []
        return words

    def set_words(self, words):
        self.words = words


# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@inlineCallbacks
def main(session, details):
    """Main function to test DialogueManager with Dutch and English."""
    logger.info("WAMP session established")

    # Initialize DialogueManager with dummy STT
    stt = DummySTT()
    dialogue_manager = DialogueManager(session, stt)

    # Ask for name
    yield dialogue_manager.say("Hello! What's your name?", gesture="wave")

    # Simulate user saying "John" (replace with real input in practice)
    stt.set_words(["John"])
    name = yield dialogue_manager.listen(timeout=5)
    if not name:
        name = "friend"
    else:
        name = name.strip().split()[-1]  # Take the last word as the name

    # Test say with Dutch and English
    test_text = f"Nice to meet you, {name}! Let's test some words. " \
                "In Dutch, chair is <nl>stoel</nl>, and table is <nl>tafel</nl>."
    yield dialogue_manager.say(test_text, gesture="point")

    # Wait a bit before ending
    yield sleep(5)
    logger.info("Test complete")


if __name__ == "__main__":
    # Set up WAMP component
    wamp = Component(
        transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0
        }],
        realm="rie.67e12f7d540602623a34dfbb",
    )
    wamp.on_join(main)
    run([wamp])