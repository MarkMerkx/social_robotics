from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from play_game import play_game
from alpha_mini_rug.speech_to_text import SpeechToText
import logging

# Initialize SpeechToText globally
stt = SpeechToText()

def on_microphone_data(data):
    """
    Callback to process microphone data.
    """
    stt.listen_continues(data)

@inlineCallbacks
def main(session, details):
    """
    Main function called when the WAMP session is joined.
    Sets up the behavior and starts the game.
    """
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    yield session.call("rie.dialogue.say", text="Initializing the game...")
    yield sleep(2)

    # Subscribe to the microphone stream for continuous STT updates.
    yield session.subscribe(on_microphone_data, "rom.sensor.microphone.stream")

    # Start the guessing game.
    yield play_game(session)

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
    realm="rie.67a4897385ba37f92bb13c6d",
)

wamp.on_join(main)

if __name__ == "__main__":
    run([wamp])