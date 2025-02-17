import os
import json
import logging
from twisted.internet.defer import inlineCallbacks, DeferredList
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement  # Make sure this import path is correct

logger = logging.getLogger(__name__)

# Load the gesture library once.
GESTURE_FILE = os.path.join(os.path.dirname(__file__), "gestures.json")
try:
    with open(GESTURE_FILE, "r") as f:
        GESTURE_LIBRARY = json.load(f)
    logger.debug("Loaded gesture library with keys: %s", list(GESTURE_LIBRARY.keys()))
except Exception as e:
    logger.error("Could not load gesture library: %s", e)
    GESTURE_LIBRARY = {}


@inlineCallbacks
def say_animated(session, text, gesture_name=None):
    """
    Speaks the given text (via the dialogue system) while concurrently performing a gesture.

    Args:
        session: The current WAMP session.
        text (str): The dialogue text.
        gesture_name (str, optional): The name of the gesture to perform.

    The function returns when both the dialogue and movement are complete.
    """
    logger.debug("say_animated called with text: '%s' and gesture: %s", text, gesture_name)

    # Start the dialogue.
    d_dialogue = session.call("rie.dialogue.say", text=text)

    # If a gesture is specified and found in our library, perform it.
    if gesture_name and gesture_name in GESTURE_LIBRARY:
        frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if frames:
            logger.debug("Performing gesture '%s' with %d keyframes", gesture_name, len(frames))
            d_movement = perform_movement(session, frames, mode="linear", sync=True, force=False)
        else:
            logger.warning("Gesture '%s' found but has no keyframes", gesture_name)
            d_movement = None
    else:
        d_movement = None

    # Wait concurrently for both the dialogue and movement (if any) to finish.
    if d_movement:
        yield DeferredList([d_dialogue, d_movement])
    else:
        yield d_dialogue
