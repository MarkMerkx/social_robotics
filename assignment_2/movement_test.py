from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from say_animated import say_animated
from alpha_mini_rug.speech_to_text import SpeechToText
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


@inlineCallbacks
def main(session, details):
    # Initialize a single SpeechToText instance.
    stt = SpeechToText()
    stt.silence_time = 1.0
    stt.silence_threshold2 = 200
    stt.logging = False

    # Test an animated speech call with a beat gesture.
    yield say_animated(session, "Hello, I hope you're having a great day!", gesture_name="beat_gesture")
    yield sleep(2)
    # Test an animated speech call with an iconic gesture.
    yield say_animated(session, "Goodbye!", gesture_name="goodbye_wave")

    # Terminate the session after testing.
    session.leave()


wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.67adc40d85ba37f92bb17029",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
