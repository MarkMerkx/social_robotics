# main.py
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

"""
TODO:

Implement a multi language (NL-EN) "I spy game" - only give the colour of the object/thing at first
Dialogue will remain in English - the words will be guessed in dutch.

Features
1. Face tracking - when the robot is not scanning 
2. Robot vision (object recognition) using either the chatGTP api vision or yolov11
 -- Determine certain FOV (make multiple images +/- 45 degrees)
 -- Scan all objects 
 ** Optionally make the robot turn around or do a full 360
3. Point to a "to be guessed object"
4. Integrate it both ways (child guesses/robot guesses)
5. Multi language (dutch/english, dialogue in english, guessed word in dutch)
6. Looking around/scanning gesture
7. Dynamic difficulty
 -- If guessed within < rounds/turns
 -- Give different starting hint
 -- increase word complexity
8. Introduction/get childs name
9. Correct childs speech if confidence of STT > x
10. Additional reasoning steps
 -- Repetition of guesses/words
 -- Reprompting after silence
11. Additional gestures when the robot is thinking (think iconic gesture)
12.* Sentiment analysis of childs emotion -> confused or disinterested - try to grab attention - measure attention span
13. Give hints (shape, size, usage)
14. Give a fun fact after guessing it or an additional dutch word that relates to it, or synonyms
15. Change STT to accept both dutch and english answers, determine which has been returned.
16. Contextual words - based on usage or something
17. Positive reinforcement
18. * Play custom sounds - if it concerns an animal, what sound does it make?
19. Generally improve the flow

"""


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
    realm="rie.67d2ae3c99b259cf43b05300",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
