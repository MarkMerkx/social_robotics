from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from time import time
import cv2 as cv
import numpy as np
import wave
import os
from alpha_mini_rug.speech_to_text import SpeechToText

# Create an instance of the SpeechToText class
audio_processor = SpeechToText()

# Adjusting necessary parameters
audio_processor.silence_time = 0.5  # Time to stop recording audio
audio_processor.silence_threshold2 = 100  # Sound below this is considered silence
audio_processor.logging = False  # Set to True for detailed logs

@inlineCallbacks
def STT_continuous(session):
    info = yield session.call("rom.sensor.hearing.info")
    print("hearing info:")
    print(info)

    yield session.call("rom.sensor.hearing.sensitivity", 1650)
    yield session.call("rie.dialogue.config.language", lang="en")
    yield session.call("rie.dialogue.say", text="Say something")

    print("Listening to audio...")

    yield session.subscribe(audio_processor.listen_continues, "rom.sensor.hearing.stream")
    yield session.call("rom.sensor.hearing.stream")

    while True:
        if not audio_processor.new_words:
            yield sleep(0.5)  # Prevents server crashes due to excessive calls
            print("Waiting...")
        else:
            word_array = audio_processor.give_me_words()
            print("Processing words...")
            print(word_array[-3:])  # Print last 3 sentences
            audio_processor.loop()

@inlineCallbacks
def main(session, details):
    # Define the output file path
    output_dir = "output"
    output_file = os.path.join(output_dir, "output.wav")

    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Create the file if it doesn't exist
    if not os.path.exists(output_file):
        with open(output_file, "wb") as f:
            f.write(b"")  # Write an empty bytes string to create the file

    yield STT_continuous(session)
    session.leave()

# Define the WAMP component
wamp = Component(
    transports=[
        {
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0,
        }
    ],
    realm="rie.67a3416c85ba37f92bb135d2",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])
