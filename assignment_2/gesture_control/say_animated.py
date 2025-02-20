import os
import json
import logging
import random
import time
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement

# Import the new gesture generation and smoothing functions.
from ..gesture_control.generate_frames import generate_beat_frames
from ..gesture_control.smoothing import smooth_predefined_frames, smooth_keyframes

logging.basicConfig(
    format='%(asctime)s GESTURE HANDLER %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Load the gesture library once.
GESTURE_FILE = os.path.join(os.path.dirname(__file__), "../gestures.json")
try:
    with open(GESTURE_FILE, "r") as f:
        GESTURE_LIBRARY = json.load(f)
    logger.debug("Loaded gesture library with keys: %s", list(GESTURE_LIBRARY.keys()))
except Exception as e:
    logger.error("Could not load gesture library: %s", e)
    GESTURE_LIBRARY = {}

# Define a neutral pose for head and arms.
NEUTRAL_POSE_FRAMES = [
    {
        "time": 0.0,
        "data": {
            "body.head.yaw": 0.0,
            "body.head.roll": 0.0,
            "body.head.pitch": 0.0,
            "body.arms.left.upper.pitch": 0.0,
            "body.arms.right.upper.pitch": 0.0
        }
    }
]


@inlineCallbacks
def loop_gesture(session, dialogue_deferred, start_time, estimated_duration):
    """
    Repeatedly perform the given (beat) gesture, optionally with noise, until
    (1) the TTS is finished, or
    (2) the estimated TTS duration is exceeded.
    """
    iteration = 0
    # movement_duration matches the total duration used in generate_beat_frames
    movement_duration = 1.0  # 2 seconds


    while not dialogue_deferred.called:
        # 1) Generate on-the-fly
        logger.debug("Generating beat gesture frames (2s).")
        frames = generate_beat_frames(duration=1000, scale=0.5)

        # 2) Smooth them
        frames = smooth_keyframes(frames, steps=1)
        logger.debug("Beat frames after smoothing: %s", frames)
        elapsed = time.time() - start_time
        logger.debug(
            "Loop gesture iteration %d; elapsed time: %.2f (estimated: %.2f)",
            iteration, elapsed, estimated_duration
        )

        # If TTS has gone on as long as we estimate, break out
        if elapsed >= estimated_duration:
            logger.debug("Elapsed time >= estimated duration. Breaking out of loop.")
            break

        iteration += 1


        # Perform movement in async mode
        perform_movement(session, frames, mode="linear", sync=False, force=True)

        # Wait for it to finish
        yield sleep(movement_duration)

    logger.debug("Exiting gesture loop after %d iterations.", iteration)


@inlineCallbacks
def perform_single_gesture(session, frames):
    logger.debug("Performing single gesture once with frames: %s", frames)

    perform_movement(session, frames, mode="last", sync=False, force=True)
    # For example, wait for the final frame's time + some margin:
    max_time_ms = frames[-1]["time"]
    yield sleep(max_time_ms / 1000.0)

    logger.debug("Single gesture completed.")



@inlineCallbacks
def say_animated(session, text, gesture_name=None):
    """
    Animated speech:
    - if gesture_name == "beat_gesture", generate frames, smooth them, then loop.
    - if gesture_name is in GESTURE_LIBRARY, run it once, with smoothing if desired.
    - else skip gestures.

    We estimate TTS duration by 0.4s/word and stop the loop if that time is exceeded
    or the TTS finishes earlier, whichever first.
    """
    logger.debug("say_animated called with text: '%s' and gesture: %s", text, gesture_name)

    # Start TTS
    start_time = time.time()
    dialogue_deferred = session.call("rie.dialogue.say", text=text)

    # Estimate TTS duration
    word_count = len(text.split())
    estimated_duration = word_count * 0.4
    logger.debug("Estimated speech duration: %.2f seconds", estimated_duration)

    # Decide gesture approach
    if gesture_name == "beat_gesture":
        # Loop until TTS done or estimate exceeded
        yield loop_gesture(session, dialogue_deferred, start_time, estimated_duration)

    elif gesture_name in GESTURE_LIBRARY:
        # 1) Load from library
        frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if not frames:
            logger.warning("Gesture '%s' found in library but has no keyframes!", gesture_name)
            pass
        else:
            # 2) Smooth them once (choose your function or steps).
            logger.debug("Iconic frames before smoothing: %s", frames)
            frames = smooth_predefined_frames(frames, steps=1)
            logger.debug("Iconic frames after smoothing: %s", frames)

            # 3) Perform gesture once
            yield perform_single_gesture(session, frames)
    else:
        logger.debug("Gesture '%s' not found or None specified; skipping gesture.", gesture_name)

    # Wait for TTS to finish
    yield dialogue_deferred
    logger.debug("Dialogue finished; say_animated complete.")
