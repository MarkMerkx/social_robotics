import os
import json
import logging
import random
import re
import time
from twisted.internet.defer import inlineCallbacks, DeferredList
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement

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


def add_noise_to_frames(frames, time_noise=50, angle_noise=0.05):
    """
    Returns a new list of frames with random noise added.

    Args:
        frames (list): A list of keyframe dictionaries.
        time_noise (float): Maximum noise in ms to add/subtract from the frame's time.
        angle_noise (float): Maximum noise to add/subtract from each joint angle.

    Returns:
        list: The list of noisy frames.
    """
    noisy_frames = []
    for frame in frames:
        # Add noise to time and angles.
        noisy_time = frame.get("time", 0.0) + random.uniform(-time_noise, time_noise)
        noisy_data = {
            joint: angle + random.uniform(-angle_noise, angle_noise)
            for joint, angle in frame.get("data", {}).items()
        }
        noisy_frames.append({"time": frame.get("time", 0.0), "data": noisy_data})
    return noisy_frames


@inlineCallbacks
def loop_gesture(session, frames, dialogue_deferred, start_time, estimated_duration):
    """
    Repeatedly perform the given gesture (with noise) until the dialogue is finished
    or our estimated TTS time is exceeded.
    """
    iteration = 0
    while not dialogue_deferred.called:
        elapsed = time.time() - start_time
        logger.debug("Loop gesture iteration %d; elapsed time: %.2f (estimated: %.2f)",
                     iteration, elapsed, estimated_duration)
        if elapsed >= estimated_duration:
            logger.debug("Elapsed time >= estimated duration. Breaking out of loop.")
            break

        iteration += 1


        movement_duration = 2.0
        noisy_frames = add_noise_to_frames(frames)

        # (2) Start the motion in async mode if your library is truly asynchronous:
        perform_movement(session, noisy_frames, mode="linear", sync=False, force=False)

        # (3) Wait for the motion to finish:
        yield sleep(movement_duration)

    logger.debug("Exiting gesture loop after %d iterations.", iteration)


@inlineCallbacks
def say_animated(session, text, gesture_name=None):
    """
    Aimated speech that estimates the speech duration and continuously loops a gesture
    (with random noise) while the dialogue is playing. The gesture loop stops either when the dialogue finishes
    or when the estimated duration is reached.

    Since our gestures already return to neutral, no additional reset is performed.
    """
    logger.debug("say_animated_experimental called with text: '%s' and gesture: %s", text, gesture_name)
    # Record start time.
    start_time = time.time()
    # Start the dialogue.
    dialogue_deferred = session.call("rie.dialogue.say", text=text)

    # Estimate speech duration using a simple heuristic (0.4 sec per word)
    word_count = len(text.split())
    estimated_duration = word_count * 0.4
    logger.debug("Estimated speech duration: %.2f seconds", estimated_duration)

    if gesture_name and gesture_name in GESTURE_LIBRARY:
        gesture_frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if gesture_frames:
            logger.debug("Starting gesture loop for '%s'", gesture_name)
            yield loop_gesture(session, gesture_frames, dialogue_deferred, start_time, estimated_duration)
        else:
            logger.warning("Gesture '%s' found but has no keyframes", gesture_name)
    else:
        logger.debug("No valid gesture specified; skipping gesture loop.")


    # Wait for dialogue to finish.
    yield dialogue_deferred
    logger.debug("Dialogue finished; say_animated_experimental complete.")
