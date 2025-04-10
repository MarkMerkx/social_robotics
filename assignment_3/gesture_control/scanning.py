"""
Scanning gesture control module.

Provides functions to control the robot's head and body movements for scanning
the environment, with both static field of view and 360-degree scanning modes.
"""

import json
import logging
import math
import os

from alpha_mini_rug import perform_movement
from autobahn.twisted.util import sleep
from twisted.internet.defer import inlineCallbacks
from assignment_3.vision.image_capture import initialize_image_directory, capture_image
from assignment_3.utils.helpers import process_detected_objects
from assignment_3.vision.object_recognition import detect_objects
logger = logging.getLogger(__name__)

# Try to load gestures.json
GESTURES_FILE = "gestures.json"
GESTURES = {}

if os.path.exists(GESTURES_FILE):
    try:
        with open(GESTURES_FILE, 'r') as f:
            GESTURES = json.load(f)
        logger.info(f"Loaded gestures from {GESTURES_FILE}")
    except Exception as e:
        logger.error(f"Error loading gestures file: {e}")

# Joint limits and movement time information
# Format: (min_angle, max_angle, minimum_time_ms)
JOINT_LIMITS = {
    "body.head.yaw": (-0.874, 0.874, 600),      # Head turn left/right
    "body.head.roll": (-0.174, 0.174, 400),     # Head tilt left/right
    "body.head.pitch": (-0.174, 0.174, 400),    # Head tilt up/down
    "body.torso.yaw": (-0.874, 0.874, 1000),    # Torso rotation
}

# Scanning parameters
DEFAULT_HEAD_YAW_RANGE = [-0.6, 0.0, 0.6]  # Left, center, right
DEFAULT_HEAD_PITCH_RANGE = [0.0]           # Single pitch level
MOVEMENT_DELAY = 1.2                                 # Delay between movements (seconds)
STABILIZATION_DELAY = 1.0                            # Delay for camera stabilization (seconds)

# Scan modes
MODE_STATIC = "static"  # Static field of view (only head movement)
MODE_360 = "360"        # 360-degree scan (robot turns in a circle)


@inlineCallbacks
def capture_and_detect(session, yaw, pitch, **extra_context):
    """
    Capture an image at the given position and detect objects.

    :param session: The WAMP session object.
    :param yaw: Yaw angle in radians.
    :param pitch: Pitch angle in radians.
    :param extra_context: Additional context (e.g., turn, orientation, position_id).
    :return: Dictionary of detected objects.
    """
    try:
        # Capture the image
        result = yield capture_image(session, yaw, pitch)
        if not result:
            logger.warning("Failed to capture image")
            return {}

        image, _ = result

        # Prepare position info for object detection
        position_info = {
            'yaw': yaw,
            'pitch': pitch,
            'yaw_deg': math.degrees(yaw),
            'pitch_deg': math.degrees(pitch),
            **extra_context  # Includes turn, orientation, position_id, etc.
        }

        # Detect objects (using ChatGPT Vision by default for I Spy game)
        detected_objects, annotated_filename = detect_objects(
            image,
            position_info=position_info,
            use_chatgpt=True,  # Optimized for feature detection in I Spy
            use_yolo=False     # Disable YOLO unless specified otherwise
        )

        logger.info(f"Captured and annotated image: {annotated_filename}")
        return detected_objects

    except Exception as e:
        logger.error(f"Error in capture_and_detect: {e}")
        return {}

@inlineCallbacks
def run_scan(session, mode=MODE_STATIC, use_yolo=False):
    """
    Perform a scan and return detected objects.

    :param session: The WAMP session object.
    :param mode: Scan mode (MODE_STATIC or MODE_360).
    :param use_yolo: Whether to use YOLO for object detection (default: False).
    :return: Tuple of (scan_results, detected_objects).
    """
    mode_name = "360-degree" if mode == MODE_360 else "static"
    logger.info(f"Starting {mode_name} environment scan")

    # Announce the scan
    yield session.call("rie.dialogue.say", text=f"Starting {mode_name} environment scan")

    # Extra parameters for the capture callback
    extra_params = {"use_yolo": use_yolo}

    # Perform the scan
    scan_results, detected_objects = yield perform_scan(
        session,
        mode=mode,
        capture_callback=capture_and_detect,
        process_callback=process_detected_objects,
        extra_context=extra_params
    )

    # Log the results
    object_count = len(detected_objects)
    if object_count > 0:
        logger.info(f"Scan complete. Detected {object_count} objects.")
    else:
        logger.info("Scan complete. No objects detected.")
        yield session.call("rie.dialogue.say", text="I didn’t detect any objects.")

    return scan_results, detected_objects


@inlineCallbacks
def move_head_to_position(session, yaw, pitch, move_time=1500):
    """
    Move the robot's head to a specific position with proper timing.

    :param session: The WAMP session
    :type session: Component
    :param yaw: Target yaw angle in radians
    :type yaw: float
    :param pitch: Target pitch angle in radians
    :type pitch: float
    :param move_time: Minimum time for the movement in milliseconds
    :type move_time: int
    :return: Success flag
    :rtype: bool
    """
    try:
        # Create movement frames for head position with explicit time values
        frames = [
            {
                "time": 0,  # Start time
                "data": {
                    "body.head.yaw": 0.0,  # Start from current position or center
                    "body.head.pitch": 0.0
                }
            },
            {
                "time": move_time,  # End time in milliseconds
                "data": {
                    "body.head.yaw": yaw,
                    "body.head.pitch": pitch
                }
            }
        ]

        # Execute movement with a safe timing
        logger.info(f"Moving head to yaw={yaw:.2f}, pitch={pitch:.2f} with time={move_time}ms")
        yield perform_movement(session, frames, mode="linear", sync=True, force=True)

        # Allow time to stabilize
        yield sleep(STABILIZATION_DELAY)  # Give extra time to ensure stability

        logger.debug(f"Moved head to yaw={yaw:.2f}, pitch={pitch:.2f}")
        return True

    except Exception as e:
        logger.error(f"Error moving head: {e}")
        return False


@inlineCallbacks
def turn_robot(session, direction="right"):
    """
    Turn the robot's body in the specified direction.

    :param session: The WAMP session
    :type session: Component
    :param direction: Direction to turn ("right" or "left")
    :type direction: str
    :return: Success flag
    :rtype: bool
    """
    try:
        # Use BlocklyTurnRight or BlocklyTurnLeft behavior
        behavior_name = f"BlocklyTurn{direction.capitalize()}"

        logger.info(f"Turning robot {direction} using {behavior_name}")
        yield session.call("rom.optional.behavior.play", name=behavior_name)

        # Wait for turn to complete
        yield sleep(3.0)  # Give enough time for the turn to complete

        return True
    except Exception as e:
        logger.error(f"Error turning robot {direction}: {e}")
        return False


@inlineCallbacks
def perform_scanning_gesture(session):
    """
    Perform a predefined scanning gesture to indicate the robot is looking around.

    :param session: The WAMP session
    :type session: Component
    :return: Success flag
    :rtype: bool
    """
    try:
        # Check if scanning gesture is defined in gestures.json
        if 'scan_gesture' in GESTURES:
            frames = GESTURES['scan_gesture'].get('keyframes', [])

            if frames:
                logger.info("Performing scanning gesture from gestures.json")
                yield perform_movement(session, frames, mode="linear", sync=True, force=True)
                yield sleep(1.0)  # Add a small delay after the gesture
                return True

        # Fallback to a simplified scanning gesture with good timing
        logger.info("Performing fallback scanning gesture")
        frames = [
            {
                "time": 0,
                "data": {
                    "body.head.yaw": 0.0,
                    "body.head.pitch": 0.0,
                    "body.head.roll": 0.0
                }
            },
            {
                "time": 1200,  # Slower movement
                "data": {
                    "body.head.yaw": 0.6,
                    "body.head.pitch": 0.0,
                    "body.head.roll": 0.0
                }
            },
            {
                "time": 2400,  # Slower movement
                "data": {
                    "body.head.yaw": -0.6,
                    "body.head.pitch": 0.0,
                    "body.head.roll": 0.0
                }
            },
            {
                "time": 3600,  # Slower movement
                "data": {
                    "body.head.yaw": 0.0,
                    "body.head.pitch": 0.0,
                    "body.head.roll": 0.0
                }
            }
        ]

        yield perform_movement(session, frames, mode="linear", sync=True, force=True)
        yield sleep(1.0)  # Add a small delay after the gesture
        return True

    except Exception as e:
        logger.error(f"Error performing scanning gesture: {e}")
        return False


@inlineCallbacks
def scan_position_and_capture(session, yaw, pitch, capture_callback, **extra_context):
    """
    Move to a specific position, stabilize, and capture an image.

    :param session: The WAMP session
    :type session: Component
    :param yaw: Yaw angle in radians
    :type yaw: float
    :param pitch: Pitch angle in radians
    :type pitch: float
    :param capture_callback: Function to call to capture image once positioned
    :type capture_callback: callable
    :param extra_context: Additional context information like turn number and rotation
    :return: Object detection results if capture_callback is provided
    :rtype: dict or None
    """
    try:
        # Determine head orientation based on yaw angle
        if yaw < -0.5:
            orientation = "right"
        elif yaw > 0.5:
            orientation = "left"
        else:
            orientation = "middle"
        logger.debug(f"Current yaw: {yaw}, current position: {orientation} ")

        # Create position identifier (turn_orientation)
        turn = extra_context.get('turn', 0)
        position_id = f"{turn}_{orientation}"

        # Add orientation and position_id to extra_context
        extra_context["orientation"] = orientation
        extra_context["position_id"] = position_id

        # First, move the head to the target position
        logger.info(
            f"Moving to position yaw={yaw:.2f}, pitch={pitch:.2f}, orientation={orientation}, position={position_id}")

        # Move with generous timing - explicitly setting movement time
        move_success = yield move_head_to_position(session, yaw, pitch, move_time=1500)
        if not move_success:
            logger.warning("Failed to move head to target position")
            return None

        # Additional stabilization time for the camera
        yield sleep(STABILIZATION_DELAY)

        # Only capture and process if we have a callback function
        if capture_callback:
            # Call the capture callback directly with extra context
            try:
                result = yield capture_callback(session, yaw, pitch, **extra_context)
                return result
            except Exception as e:
                logger.error(f"Error in capture callback: {e}")

        return None

    except Exception as e:
        logger.error(f"Error in scan_position_and_capture: {e}")
        return None


@inlineCallbacks
def scan_area(session, yaw_angles, pitch_angles, capture_callback, process_callback=None, extra_context=None):
    """
    Scan an area by moving the head through the specified angles and capture images.

    :param session: The WAMP session
    :type session: Component
    :param yaw_angles: List of yaw angles to scan at
    :type yaw_angles: list
    :param pitch_angles: List of pitch angles to scan at
    :type pitch_angles: list
    :param capture_callback: Function to call to capture images
    :type capture_callback: callable
    :param process_callback: Function to call to process results
    :type process_callback: callable
    :param extra_context: Additional context information to pass to capture callback
    :type extra_context: dict
    :return: Dictionary of positions scanned and detected objects
    :rtype: dict
    """
    all_objects = {}
    scan_results = {}

    # Extra context contains information like current turn and cumulative rotation
    if extra_context is None:
        extra_context = {}

    try:
        # Reset head position before starting with explicit timing
        yield move_head_to_position(session, 0.0, 0.0, move_time=1500)

        # Scan through each position
        for i, yaw in enumerate(yaw_angles):
            logger.info(f"Scanning position {i + 1}/{len(yaw_angles)}, yaw={yaw:.2f}")

            for j, pitch in enumerate(pitch_angles):
                logger.info(f"  Scanning at pitch {j + 1}/{len(pitch_angles)}, pitch={pitch:.2f}")

                # Position key for storing results
                position_key = f"yaw{yaw:.2f}_pitch{pitch:.2f}"

                # Capture and process image at this position with extra context
                objects = yield scan_position_and_capture(session, yaw, pitch, capture_callback, **extra_context)

                # Store the results
                scan_results[position_key] = {
                    'yaw': yaw,
                    'pitch': pitch,
                    'yaw_deg': math.degrees(yaw),
                    'pitch_deg': math.degrees(pitch),
                    'objects': objects
                }

                # Process objects if we have any
                if objects and process_callback:
                    all_objects = process_callback(all_objects, objects)

                # Brief pause between captures
                yield sleep(0.3)

            # Longer pause between yaw positions
            yield sleep(0.5)

        # Return to center position with explicit timing
        yield move_head_to_position(session, 0.0, 0.0, move_time=1500)

        return scan_results, all_objects

    except Exception as e:
        logger.error(f"Error in scan_area: {e}")

        # Try to return to center position
        try:
            yield move_head_to_position(session, 0.0, 0.0, move_time=1500)
        except:
            pass

        return scan_results, all_objects


@inlineCallbacks
def perform_static_scan(session, capture_callback, process_callback=None, extra_context=None):
    """
    Perform a static scan using only head movements.

    :param session: The WAMP session
    :param capture_callback: Function to call to capture images
    :param process_callback: Function to call to process results
    :param extra_context: Additional context to pass to capture_callback
    :return: (scan_results, all_objects)
    """
    logger.info("Starting static scan (head movement only)")

    # Use default angles: left, center, right
    yaw_angles = DEFAULT_HEAD_YAW_RANGE
    pitch_angles = DEFAULT_HEAD_PITCH_RANGE

    # If no extra_context dict is given, create one
    if extra_context is None:
        extra_context = {}

    # Optional pause before we start
    yield sleep(1.0)

    # Move head to neutral (0, 0)
    logger.info("Centering head before starting scan")
    yield move_head_to_position(session, 0.0, 0.0, move_time=1500)
    yield sleep(0.5)  # small delay for stability

    # Mark which turn we are on (used in scans)
    extra_context["turn"] = 0
    extra_context["cumulative_rotation"] = 0

    # Now do the actual scanning
    logger.info("Executing static scan pattern with improved head movement")
    scan_results, all_objects = yield scan_area(
        session,
        yaw_angles,
        pitch_angles,
        capture_callback,
        process_callback,
        extra_context=extra_context
    )

    # Return head to center again at the end
    logger.info("Returning head to center position")
    yield move_head_to_position(session, 0.0, 0.0, move_time=1800)

    logger.info(f"Static scan complete. Scanned {len(scan_results)} positions.")
    return scan_results, all_objects



@inlineCallbacks
def perform_360_scan(session, capture_callback, process_callback=None, extra_context=None):
    """
    Perform a 360-degree scan by rotating the robot and scanning at each position.

    :param session: The WAMP session
    :type session: Component
    :param capture_callback: Function to call to capture images
    :type capture_callback: callable
    :param process_callback: Function to call to process results
    :type process_callback: callable
    :param extra_context: Additional context to pass to capture_callback
    :type extra_context: dict
    :return: Dictionary of scan results and all detected objects
    :rtype: tuple(dict, dict)
    """
    logger.info("Starting 360-degree scan")

    turns = 3  # 120 degree turns for full coverage
    turn_angle = 120  # Degrees per turn
    cumulative_rotation = 0
    all_scan_results = {}
    all_detected_objects = {}

    # Initialize extra_context if it's None
    if extra_context is None:
        extra_context = {}

    for turn in range(turns):
        logger.info(f"Performing scan at rotation {cumulative_rotation} degrees (turn {turn + 1}/{turns})")

        # Make sure the head is centered before scanning each section - with explicit timing
        yield move_head_to_position(session, 0.0, 0.0, move_time=1500)
        yield sleep(0.5)  # Brief pause to stabilize

        # Merge base extra_context with turn-specific context
        turn_context = extra_context.copy()
        turn_context.update({
            "turn": turn,
            "cumulative_rotation": cumulative_rotation
        })

        # Perform the scan at the current rotation position
        logger.info(f"Scanning sector {turn + 1}/{turns}")
        scan_results, objects = yield scan_area(
            session,
            DEFAULT_HEAD_YAW_RANGE,  # Use all defined yaw angles
            DEFAULT_HEAD_PITCH_RANGE,
            capture_callback,
            process_callback,
            extra_context=turn_context
        )

        # Merge the results
        all_scan_results.update(scan_results)
        if objects and process_callback:
            all_detected_objects = process_callback(all_detected_objects, objects)

        if turn < turns - 1:  # Don't turn after the last scan
            # Reset head to center before turning the body - with explicit timing
            logger.info("Centering head before body turn")
            yield move_head_to_position(session, 0.0, 0.0, move_time=1500)
            yield sleep(0.5)  # Brief pause

            # Turn robot and update rotation tracking
            logger.info(f"Turning robot {turn_angle} degrees right (turn {turn + 1}/{turns})")
            yield turn_robot(session, "right")
            cumulative_rotation = (cumulative_rotation + turn_angle) % 360

            # Give the robot time to stabilize after turning
            yield sleep(1.0)

    # Reset head position at the end of the scan - with explicit timing
    logger.info("Resetting head position at the end of scan")
    yield move_head_to_position(session, 0.0, 0.0, move_time=1500)

    # Additional turn to return to start position
    logger.info("Turning robot to return to start position")
    yield turn_robot(session, "right")

    logger.info("360-degree scan complete")
    return all_scan_results, all_detected_objects


@inlineCallbacks
def perform_scan(session, mode=MODE_STATIC, capture_callback=None, process_callback=None, extra_context=None):
    """
    Perform a scan using the specified mode.

    :param session: The WAMP session
    :type session: Component
    :param mode: Scan mode ("static" or "360")
    :return: Dictionary of scan results and all detected objects
    :rtype: tuple(dict, dict)
    """
    # Pass along extra_context to the appropriate scan function
    if mode == MODE_360:
        return (yield perform_360_scan(session, capture_callback, process_callback, extra_context=extra_context))
    else:
        return (yield perform_static_scan(session, capture_callback, process_callback, extra_context=extra_context))


@inlineCallbacks
def point_to_object(session, obj_info, use_torso=True):
    """
    Point the robot at the given object's angle, possibly rotating the torso as well.
    Also speak the object's name in English and Dutch.

    :param session: WAMP session
    :param obj_info: Dict with keys like "yaw", "pitch", "cumulative_rotation",
                     "name", "dutch_name"
    :param use_torso: Whether to rotate the torso for large angles
    """
    try:
        # 1) Read relevant fields from obj_info
        angle_deg = obj_info.get('yaw', 0)
        pitch_deg = obj_info.get('pitch', 0)
        cumulative_rotation = obj_info.get('cumulative_rotation', 0)
        english_name = obj_info.get('name', 'unknown')
        dutch_name = obj_info.get('dutch_name', 'onbekend')

        logger.info(f"Request to point to object: {english_name} / {dutch_name} at yaw={angle_deg}, pitch={pitch_deg}, cumulative={cumulative_rotation}")

        # 2) Possibly add the cumulative rotation if the robot is in 360 mode
        # If your code always sets 'cumulative_rotation'=0 for static mode, that’s fine
        final_angle = angle_deg + cumulative_rotation

        # Normalize final_angle into [-180, +180]
        final_angle = ((final_angle + 180) % 360) - 180

        logger.info(f"Computed final angle (after rotation) = {final_angle:.1f} degrees")

        # 3) Optionally speak the name in English and Dutch
        # For example: "In English, it's called phone, and in Dutch, telefoon!"
        # You can reorder or modify the text to your preference
        speech_text = f"In English, it's called {english_name}, and in Dutch, we call it {dutch_name}!"
        yield session.call("rie.dialogue.say", text=speech_text)

        # 4) Possibly rotate torso if final_angle is large
        #    We'll do a naive approach: if angle is outside ±45°, rotate torso by half the angle
        torso_rotation = 0
        if use_torso and abs(final_angle) > 45:
            torso_rotation = final_angle * 0.5
            # Clamp torso within [-50, 50] degrees, for example
            torso_rotation = max(min(torso_rotation, 50), -50)
            logger.info(f"Rotating torso by {torso_rotation:.1f} degrees first.")
            yield _rotate_torso(session, torso_rotation)
            # Subtract that from final_angle
            final_angle -= torso_rotation

        # 5) Now we only have 'final_angle' for the head
        #    Also clamp pitch if needed, e.g. pitch in [-30..30] deg
        head_pitch = max(min(pitch_deg, 30), -30)

        # 6) Convert these angles to radians
        head_yaw_rads = math.radians(final_angle)
        head_pitch_rads = math.radians(head_pitch)

        # 7) Move the head
        logger.info(f"Final head yaw={final_angle:.1f}°, pitch={head_pitch:.1f}°")
        yield move_head_to_position(session, head_yaw_rads, head_pitch_rads, move_time=1500)

        # 8) Execute the pointing gesture with the arms, as in your existing fallback code
        #    We'll pick left or right based on sign of final_angle
        #    ( >0 => left, <0 => right ), or you can keep the code from your snippet
        if final_angle >= 0:
            # left arm
            logger.info("Doing fallback left-arm pointing gesture")
            yield _fallback_left_point(session, head_yaw_rads, head_pitch_rads)
        else:
            # right arm
            logger.info("Doing fallback right-arm pointing gesture")
            yield _fallback_right_point(session, head_yaw_rads, head_pitch_rads)

        return True

    except Exception as e:
        logger.error(f"Error in point_to_object: {e}")
        # Optionally reset position
        yield _reset_arms_and_head(session)
        return False


@inlineCallbacks
def _rotate_torso(session, angle_deg):
    """
    Rotate the robot's torso by 'angle_deg' (approx) if feasible.
    Adjust frames as needed for your hardware constraints.
    """
    # Convert to radians
    angle_rads = math.radians(angle_deg)
    # Torso rotation frames (0 -> angle -> 0 if you want to keep it short)
    # Or maybe you want to keep the torso rotated. We'll assume we keep it rotated
    frames = [
        {
            "time": 0,
            "data": {
                "body.torso.yaw": 0.0
            }
        },
        {
            "time": 1500,
            "data": {
                "body.torso.yaw": angle_rads
            }
        }
    ]
    yield perform_movement(session, frames, mode="linear", sync=True, force=True)
    yield sleep(0.5)

@inlineCallbacks
def _fallback_left_point(session, yaw_rads, pitch_rads):
    """
    Fallback left-arm pointing, similar to your existing code, but extracted to a helper.
    """
    arm_frames = [
        {
            "time": 0,
            "data": {
                "body.arms.left.upper.pitch": 0.0,
                "body.arms.left.lower.roll": 0.0,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 1800,
            "data": {
                "body.arms.left.upper.pitch": -1.5,
                "body.arms.left.lower.roll": -0.7,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 4000,
            "data": {
                "body.arms.left.upper.pitch": -1.5,
                "body.arms.left.lower.roll": -0.7,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 5800,
            "data": {
                "body.arms.left.upper.pitch": 0.0,
                "body.arms.left.lower.roll": 0.0,
                "body.head.yaw": 0.0,
                "body.head.pitch": 0.0
            }
        }
    ]
    yield perform_movement(session, arm_frames, mode="linear", sync=True, force=True)

@inlineCallbacks
def _fallback_right_point(session, yaw_rads, pitch_rads):
    """
    Fallback right-arm pointing, similar to your existing code, but extracted to a helper.
    """
    arm_frames = [
        {
            "time": 0,
            "data": {
                "body.arms.right.upper.pitch": 0.0,
                "body.arms.right.lower.roll": 0.0,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 1800,
            "data": {
                "body.arms.right.upper.pitch": -1.5,
                "body.arms.right.lower.roll": -0.7,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 4000,
            "data": {
                "body.arms.right.upper.pitch": -1.5,
                "body.arms.right.lower.roll": -0.7,
                "body.head.yaw": yaw_rads,
                "body.head.pitch": pitch_rads
            }
        },
        {
            "time": 5800,
            "data": {
                "body.arms.right.upper.pitch": 0.0,
                "body.arms.right.lower.roll": 0.0,
                "body.head.yaw": 0.0,
                "body.head.pitch": 0.0
            }
        }
    ]
    yield perform_movement(session, arm_frames, mode="linear", sync=True, force=True)


@inlineCallbacks
def _reset_arms_and_head(session):
    """Just resets arms and head to neutral if pointing fails."""
    reset_frames = [
        {
            "time": 0,
            "data": {
                "body.head.yaw": 0.0,
                "body.head.pitch": 0.0,
                "body.arms.left.upper.pitch": 0.0,
                "body.arms.left.lower.roll": 0.0,
                "body.arms.right.upper.pitch": 0.0,
                "body.arms.right.lower.roll": 0.0
            }
        }
    ]
    yield perform_movement(session, reset_frames, mode="linear", sync=True, force=True)

