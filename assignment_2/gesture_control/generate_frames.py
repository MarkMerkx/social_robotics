import random
import math


def generate_beat_frames(duration=2.0, head_range=(-0.1, 0.1), arm_range=(-0.2, 0.2)):
    """
    Generate a basic beat gesture consisting of three keyframes:
    - Start: Neutral pose.
    - Peak: Randomized head and arm movement within defined ranges.
    - End: Return to neutral pose.

    Args:
        duration (float): Total duration of the gesture in seconds.
        head_range (tuple): Allowed deviation range for head joints.
        arm_range (tuple): Allowed deviation range for arm joints.

    Returns:
        list: A list of keyframes with 'time' and 'data' for each joint.
    """
    # Neutral pose for start and end.
    neutral_data = {
        "body.head.yaw": 0.0,
        "body.head.roll": 0.0,
        "body.head.pitch": 0.0,
        "body.arms.left.upper.pitch": 0.0,
        "body.arms.right.upper.pitch": 0.0
    }

    # Frame 0: Neutral at t=0.
    frame0 = {"time": 0.0, "data": neutral_data.copy()}

    # Frame 1: Peak movement at t = duration/2 with slight random deviations.
    frame1 = {
        "time": duration / 2,
        "data": {
            "body.head.yaw": random.uniform(*head_range),
            "body.head.roll": random.uniform(*head_range),
            "body.head.pitch": random.uniform(*head_range),
            "body.arms.left.upper.pitch": random.uniform(*arm_range),
            "body.arms.right.upper.pitch": random.uniform(*arm_range)
        }
    }

    # Frame 2: Return to neutral at t = duration.
    frame2 = {"time": duration, "data": neutral_data.copy()}

    return [frame0, frame1, frame2]


def ease_in_out(t):
    """
    Ease-in-out interpolation function.

    Args:
        t (float): Normalized time (0 <= t <= 1).

    Returns:
        float: Smoothed interpolation value.
    """
    return 3 * t ** 2 - 2 * t ** 3


