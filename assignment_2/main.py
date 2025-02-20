from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from twisted.internet.task import LoopingCall
from assignment_2.game_control.play_game import play_game
from alpha_mini_rug.speech_to_text import SpeechToText
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize a single SpeechToText instance
stt = SpeechToText()
stt.silence_time = 1.0
stt.silence_threshold2 = 200
stt.logging = False

def process_audio():
    """
    Continuously processes buffered audio data.
    We call only stt.loop() so that the new words remain available
    for wait_for_response to pick up.
    """
    stt.loop()

@inlineCallbacks
def main(session, details):
    """
    Main function called when the WAMP session is joined.
    Configures the microphone, subscribes to and starts the audio stream,
    launches a concurrent audio processing loop, and starts the guessing game.
    """
    # Optional behavior: play an initial animation.
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    yield session.call("rie.dialogue.say", text="Initializing the game...")
    yield sleep(2)

    # Configure the microphone sensitivity and language.
    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")

    # Subscribe to the microphone stream for continuous STT updates.
    yield session.subscribe(stt.listen_continues, "rom.sensor.hearing.stream")

    # Start the microphone stream.
    yield session.call("rom.sensor.hearing.stream")
    logger.debug("Audio stream started.")

    # Launch the audio processing loop concurrently.
    audio_loop = LoopingCall(process_audio)
    audio_loop.start(0.5)  # Process audio every 0.5 seconds.

    # Start the guessing game, passing the shared STT instance.
    yield play_game(session, stt)

    # Keep the session alive.
    while True:
        yield sleep(1)

# Configure the WAMP component.
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.67b7052ba06ea6579d140a02",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
