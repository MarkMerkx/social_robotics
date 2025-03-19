import logging
import math
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep

# Import your existing scanning methods for turning and moving head
from gesture_control.scanning import turn_robot, move_head_to_position
from alpha_mini_rug import perform_movement

logger = logging.getLogger(__name__)

@inlineCallbacks
def point_to_object(session, object_info):
    """
    Point the robot at the selected object, based on its position_id
    (e.g. '3_left', '2_middle'), plus its English/Dutch names.

    object_info should look like:
    {
      "name": "red ball",
      "dutch_name": "rode bal",
      "position_id": "3_left",   # means turn right 3 times, then final left offset
      "yaw": 0.6,                # optional
      "pitch": 0,                # optional
      ...
    }
    """
    try:
        # Speak the object name in both English and Dutch
        english_name = object_info.get("name", "unknown")
        dutch_name = object_info.get("dutch_name", "onbekend")
        speak_text = (
            f"I see a {english_name}. In Dutch, we call it {dutch_name}."
        )
        yield session.call("rie.dialogue.say", text=speak_text)

        # 1) Parse the "position_id" field: e.g. "3_left"
        position_id = object_info.get("position_id", "0_middle")
        parts = position_id.split("_")
        if len(parts) != 2:
            logger.warning(f"position_id='{position_id}' not in expected format 'X_orientation'. Using fallback=0_middle")
            parts = ["0", "middle"]

        turns_str, orientation = parts
        # Convert number of turns to integer
        try:
            turns = int(turns_str)
        except ValueError:
            logger.warning(f"Invalid turns_str='{turns_str}', defaulting to 0")
            turns = 0

        logger.info(f"Object is at position_id={position_id}: turning right {turns} times, then orientation={orientation}")

        # 2) Perform the body turns
        for i in range(turns):
            yield turn_robot(session, "right")
            yield sleep(1.0)  # small delay

        # 3) Decide the final yaw angle for the head based on orientation
        #    (You can adjust these angles as you like.)
        if orientation == "left":
            head_yaw_deg = 35  # left side
        elif orientation == "right":
            head_yaw_deg = -35 # right side
        else:  # "middle"
            head_yaw_deg = 0

        # Also handle pitch if you want
        pitch_deg = object_info.get("pitch", 0)
        # clamp pitch to safe range, e.g. -20..20
        pitch_deg = max(min(pitch_deg, 20), -20)

        # Convert to radians
        head_yaw_rads = math.radians(head_yaw_deg)
        pitch_rads = math.radians(pitch_deg)

        # 4) Move head to final orientation
        logger.info(f"Moving head to yaw={head_yaw_deg}°, pitch={pitch_deg}°")
        yield move_head_to_position(session, head_yaw_rads, pitch_rads, move_time=1500)
        yield sleep(0.5)

        # 5) Actually point with either left or right arm if we are not oriented middle
        #    For simplicity, we’ll do fallback gestures from your existing code
        if head_yaw_deg >= 0:
            logger.info("Using fallback left-arm pointing gesture")
            yield _fallback_left_point(session, head_yaw_rads, pitch_rads)
        else:
            logger.info("Using fallback right-arm pointing gesture")
            yield _fallback_right_point(session, head_yaw_rads, pitch_rads)

        logger.info("Pointing done.")
        return True

    except Exception as e:
        logger.error(f"Error in point_to_object: {e}")
        yield _reset_arms_and_head(session)
        return False


@inlineCallbacks
def _fallback_left_point(session, yaw_rads, pitch_rads):
    """Simple fallback pointing with left arm."""
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
    """Simple fallback pointing with right arm."""
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
    """
    Resets arms and head to neutral if an error occurs.
    """
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
