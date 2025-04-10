import argparse
import logging
import os

from alpha_mini_rug.speech_to_text import SpeechToText
from autobahn.twisted.component import Component, run
from autobahn.twisted.util import sleep
from twisted.internet.defer import inlineCallbacks
from twisted.internet.task import LoopingCall

from assignment_3.game_control.play_game import play_game
from assignment_3.utils.helpers import setup_logging
from assignment_3.vision.image_capture import initialize_image_directory
from assignment_3.vision.object_recognition import initialize_object_directory

setup_logging()
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs("vision", exist_ok=True)
os.makedirs("gesture_control", exist_ok=True)
os.makedirs("utils", exist_ok=True)
for directory in ["vision", "gesture_control", "utils"]:
    init_file = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            pass

initialize_image_directory()
initialize_object_directory()

# Initialize STT instance
stt = SpeechToText()
stt.silence_time = 1.0
stt.silence_threshold2 = 200
stt.logging = False

# Add command-line argument for scan mode
parser = argparse.ArgumentParser(description="I Spy Game with Alpha Mini Robot")
parser.add_argument(
    "--scan-mode",
    choices=["static", "360"],
    default="static",
    help="Set the robot's scan mode: 'static' or '360' (default: static)"
)
args = parser.parse_args()

def process_audio():
    """Continuously process buffered audio data."""
    stt.loop()

@inlineCallbacks
def main(session, details):
    """Main function called when the WAMP session is joined."""
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    yield session.call("rie.dialogue.say", text="Initializing the game...")
    yield sleep(2)

    # Configure microphone
    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    # Set initial language (DialogueManager will handle switching later)
    yield session.call("rie.dialogue.config.language", lang="en")
    stt.language_setting = "en"  # Ensure STT aligns with initial language

    # Subscribe to and start the audio stream
    yield session.subscribe(stt.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")
    logger.debug("Audio stream started.")

    # Start audio processing loop
    audio_loop = LoopingCall(process_audio)
    audio_loop.start(0.5)

    # Start the game with the STT instance and scan mode
    yield play_game(session, stt, scan_mode=args.scan_mode)

    while True:
        yield sleep(1)

wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.67e1353e540602623a34dfec",
)
wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])