import os
import json
import logging
import random
from twisted.internet.defer import inlineCallbacks, DeferredList
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement  # adjust the import path as needed

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
def say_animated(session, text, gesture_name=None):
    """
    Basic animated speech: speaks the text and performs a gesture once.
    After both dialogue and movement finish, it resets to a neutral pose in a fire-and-forget manner.
    """
    logger.debug("say_animated called with text: '%s' and gesture: %s", text, gesture_name)
    d_dialogue = session.call("rie.dialogue.say", text=text)

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

    if d_movement:
        yield DeferredList([d_dialogue, d_movement])
    else:
        yield d_dialogue

    # Fire-and-forget: reset to neutral pose without delaying the next action.
    session.call("rom.actuator.motor.write", frames=NEUTRAL_POSE_FRAMES, mode="linear", sync=True, force=False)


@inlineCallbacks
def say_animated_experimental(session, text, gesture_name=None):
    """
    Experimental animated speech that estimates the speech duration and continuously loops a gesture
    (with added random noise) while the dialogue is playing. Once the dialogue finishes, it resets the robot
    to a neutral pose using a fire-and-forget call.
    """
    logger.debug("say_animated_experimental called with text: '%s' and gesture: %s", text, gesture_name)
    # Start the dialogue.
    dialogue_deferred = session.call("rie.dialogue.say", text=text)

    # Estimate duration (simple heuristic: 0.4 sec per word)
    word_count = len(text.split())
    estimated_duration = word_count * 0.4
    logger.debug("Estimated speech duration: %.2f seconds", estimated_duration)

    loop_gesture_deferred = None
    if gesture_name and gesture_name in GESTURE_LIBRARY:
        gesture_frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if gesture_frames:
            @inlineCallbacks
            def loop_gesture():
                # Loop the gesture until the dialogue call is complete.
                while not dialogue_deferred.called:
                    noisy_frames = []
                    for frame in gesture_frames:
                        # Introduce small random noise for variety.
                        noisy_time = frame.get("time", 0.0) + random.uniform(-0.1, 0.1)
                        noisy_data = {joint: angle + random.uniform(-0.05, 0.05)
                                      for joint, angle in frame.get("data", {}).items()}
                        noisy_frames.append({"time": noisy_time, "data": noisy_data})
                    logger.debug("Performing noisy gesture loop with frames: %s", noisy_frames)
                    yield perform_movement(session, noisy_frames, mode="linear", sync=True, force=False)
                    # Short delay before repeating.
                    yield sleep(0.2)
            loop_gesture_deferred = loop_gesture()
        else:
            logger.warning("Gesture '%s' found but has no keyframes", gesture_name)
    else:
        logger.debug("No valid gesture specified; skipping gesture loop.")

    # Wait for dialogue to finish.
    yield dialogue_deferred

    session.call("rom.actuator.motor.write", frames=NEUTRAL_POSE_FRAMES, mode="linear", sync=True, force=False)
