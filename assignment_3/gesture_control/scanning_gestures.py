# assignment_3/gesture_control/scanning_gestures.py
"""
Gestures for scanning and pointing in the I Spy game.
Uses predefined keyframe animations from gestures.json for accurate and controlled movements.
"""

import os
import json
import logging
import math
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from alpha_mini_rug import perform_movement
from assignment_2.gesture_control.smoothing import smooth_predefined_frames

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load the gesture library if not already loaded
GESTURE_FILE = os.path.join(os.path.dirname(__file__), "../gestures.json")
try:
    with open(GESTURE_FILE, "r") as f:
        GESTURE_LIBRARY = json.load(f)
    logger.debug("Loaded gesture library with scanning gestures: %s",
                 [key for key in GESTURE_LIBRARY.keys() if key.startswith("scan") or key.startswith("point")])
except Exception as e:
    logger.error(f"Could not load gesture library: {e}")
    GESTURE_LIBRARY = {}


@inlineCallbacks
def perform_single_gesture(session, frames):
    """
    Perform a single gesture from predefined keyframes.

    Args:
        session: The WAMP session
        frames: List of keyframe dictionaries
    """
    logger.debug(f"Performing gesture with {len(frames)} frames")

    try:
        perform_movement(session, frames, mode="last", sync=False, force=True)
        # Wait for the gesture to complete
        max_time_ms = frames[-1]["time"]
        yield sleep(max_time_ms / 1000.0)
        logger.debug("Gesture completed")
    except Exception as e:
        logger.error(f"Error performing gesture: {e}")


@inlineCallbacks
def perform_scan_gesture(session):
    """
    Make the robot perform a simple scanning gesture, looking side to side.
    """
    if "scan_gesture" not in GESTURE_LIBRARY:
        logger.error("scan_gesture not found in library")
        return

    try:
        frames = GESTURE_LIBRARY["scan_gesture"].get("keyframes", [])
        if not frames:
            logger.warning("scan_gesture found in library but has no keyframes!")
            return

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing scan gesture: {e}")


@inlineCallbacks
def perform_scan_360(session):
    """
    Make the robot perform a full 360-degree scan using torso and head movements.
    """
    if "scan_360" not in GESTURE_LIBRARY:
        logger.error("scan_360 not found in library")
        return

    try:
        frames = GESTURE_LIBRARY["scan_360"].get("keyframes", [])
        if not frames:
            logger.warning("scan_360 found in library but has no keyframes!")
            return

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing 360 scan: {e}")


@inlineCallbacks
def perform_look_up_down(session, direction="up"):
    """
    Make the robot look up or down.

    Args:
        session: The WAMP session
        direction: "up" or "down"
    """
    gesture_name = f"look_{direction}"

    if gesture_name not in GESTURE_LIBRARY:
        logger.error(f"{gesture_name} not found in library")
        return

    try:
        frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if not frames:
            logger.warning(f"{gesture_name} found in library but has no keyframes!")
            return

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing {gesture_name}: {e}")


@inlineCallbacks
def perform_point_to(session, angle_degrees):
    """
    Make the robot point in a specific direction.

    Args:
        session: The WAMP session
        angle_degrees: Direction to point (in degrees, 0 is forward)
    """
    # Determine whether to use left or right arm based on angle
    if angle_degrees > 0:  # Positive angle is left
        gesture_name = "point_left"
    else:  # Negative angle is right
        gesture_name = "point_right"

    if gesture_name not in GESTURE_LIBRARY:
        logger.error(f"{gesture_name} not found in library")
        return

    try:
        # Get the base pointing gesture
        frames = GESTURE_LIBRARY[gesture_name].get("keyframes", [])
        if not frames:
            logger.warning(f"{gesture_name} found in library but has no keyframes!")
            return

        # Adjust the head yaw to match the specified angle
        # Find frames that modify head.yaw
        angle_radians = math.radians(angle_degrees)
        for frame in frames:
            if "body.head.yaw" in frame["data"]:
                # Adjust the yaw while respecting hardware limits (-0.874 to 0.874 radians)
                frame["data"]["body.head.yaw"] = max(-0.874, min(0.874, angle_radians))

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing pointing gesture: {e}")


@inlineCallbacks
def perform_thinking_gesture(session):
    """
    Make the robot look like it's thinking.
    """
    if "thinking" not in GESTURE_LIBRARY:
        logger.error("thinking gesture not found in library")
        return

    try:
        frames = GESTURE_LIBRARY["thinking"].get("keyframes", [])
        if not frames:
            logger.warning("thinking gesture found in library but has no keyframes!")
            return

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing thinking gesture: {e}")


@inlineCallbacks
def perform_attention_gesture(session):
    """
    Make the robot perform an attention-grabbing gesture.
    """
    if "attention_getter" not in GESTURE_LIBRARY:
        logger.error("attention_getter not found in library")
        return

    try:
        frames = GESTURE_LIBRARY["attention_getter"].get("keyframes", [])
        if not frames:
            logger.warning("attention_getter found in library but has no keyframes!")
            return

        # Smooth the frames
        frames = smooth_predefined_frames(frames, steps=1)

        # Perform the gesture
        yield perform_single_gesture(session, frames)
    except Exception as e:
        logger.error(f"Error performing attention gesture: {e}")


@inlineCallbacks
def perform_incremental_scan(session, start_angle=0, increment=15, count=24):
    """
    Make the robot perform an incremental scan, taking pictures at specified intervals.

    Args:
        session: The WAMP session
        start_angle: Starting angle in degrees (default: 0)
        increment: Angle increment in degrees (default: 15)
        count: Number of positions to scan (default: 24 for a full 360)
    """
    try:
        # Start at the initial position
        current_angle = start_angle
        yield session.call("rom.motion.joint.move", joint="body.head.yaw",
                           angle=math.radians(current_angle), speed=0.5)
        yield sleep(1.0)  # Allow time to stabilize

        # Scan at each position
        for _ in range(count):
            # At each position, look up and down
            for pitch in [0, 20, -20]:  # Default, looking up, looking down
                yield session.call("rom.motion.joint.move", joint="body.head.pitch",
                                   angle=math.ra