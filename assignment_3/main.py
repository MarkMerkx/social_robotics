"""
TODO:
1. Face tracking - when the robot is not scanning
4. Integrate it both ways (child guesses/robot guesses)
5. Multi language (dutch/english, dialogue in english, guessed word in dutch)
8. Introduction/get child's name
9. Correct child's speech if confidence of STT > x
10. Additional reasoning steps (e.g., repetition of guesses, reprompting after silence)
11. Additional gestures when the robot is thinking
12.* Sentiment analysis to detect confusion or disinterest, measure attention span
13. Give hints (shape, size, usage)
14. Give a fun fact or synonyms after guessing
15. Change STT to accept both dutch and english answers
17. Positive reinforcement
18.* Play custom sounds (e.g., if it concerns an animal)
19. Generally improve the flow

FIXME:
3. Point to a "to be guessed object" (enhance torso rotation / alignment)
7. Dynamic difficulty (if guessed within fewer rounds, give easier or harder next object)
"""

import logging
import os
from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from twisted.internet.task import LoopingCall

# Vision and logging setup
from assignment_3.utils.helpers import setup_logging
from assignment_3.vision.image_capture import initialize_image_directory
from assignment_3.vision.object_recognition import initialize_object_directory

# Our game
from assignment_3.game_control.play_game import play_game

# Speech recognition
from alpha_mini_rug.speech_to_text import SpeechToText

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Ensure directories exist
os.makedirs("vision", exist_ok=True)
os.makedirs("gesture_control", exist_ok=True)
os.makedirs("utils", exist_ok=True)

# Create __init__.py if missing, so imports work
for directory in ["vision", "gesture_control", "utils"]:
    init_file = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            pass

# Initialize image directories for scanning
initialize_image_directory()
initialize_object_directory()

# Initialize a single SpeechToText instance (adjust thresholds to your preference)
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
    launches a concurrent audio processing loop, and starts the 'play_game' logic.
    """
    # Optional "Crouch" or other initial behavior
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    yield session.call("rie.dialogue.say", text="Initializing the game...")
    yield sleep(2)

    # Configure microphone and language
    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")

    # Subscribe to the microphone stream for continuous STT
    yield session.subscribe(stt.listen_continues, "rom.sensor.hearing.stream")

    # Start mic stream
    yield session.call("rom.sensor.hearing.stream")
    logger.debug("Audio stream started.")

    # Audio processing loop
    audio_loop = LoopingCall(process_audio)
    audio_loop.start(0.5)  # process audio every 0.5 seconds

    # Start the main "play_game" flow (which now does the I Spy user guess approach)
    yield play_game(session, stt)

    # Keep the session alive
    while True:
        yield sleep(1)

# Configure WAMP
wamp = Component(
    transports=[{
        "url": "ws://wamp.robotsindeklas.nl",
        "serializers": ["msgpack"],
        "max_retries": 0
    }],
    realm="rie.67daa31e540602623a34bf03",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
