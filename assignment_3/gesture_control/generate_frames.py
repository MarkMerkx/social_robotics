# /gesture_control/generate_frames.py
import random

# Only the head and arms, removing legs since they're not being used.
# Format: joint_name: (min_angle, max_angle, min_time)
# We'll only use the (min_angle, max_angle) portion for random generation,
# ignoring 'min_time' here because the final timing adjustments
# can happen later (e.g. ensure_min_required_time).
HW_LIMITS_HEAD_ARMS = {
    "body.head.yaw": (-0.874, 0.874, 600),
    "body.head.roll": (-0.174, 0.174, 400),
    "body.head.pitch": (-0.174, 0.174, 400),
    "body.arms.left.upper.pitch": (-2.59, 1.59, 1600),
    "body.arms.right.upper.pitch": (-2.59, 1.59, 1600)
}




def _clamp(value, low, high):
    return max(low, min(value, high))

def generate_beat_frames(duration=2000, scale=1.6):
    """
    Generates a basic beat gesture (head and arms) with times in milliseconds:
    - Frame 0 at t=0 (neutral)
    - Frame 1 at t=duration/2 (peak)
    - Frame 2 at t=duration (neutral)
    Round angles to 3 decimals so we don't produce too many decimal places.
    """

    neutral_data = {
        "body.head.yaw": 0.0,
        "body.head.roll": 0.0,
        "body.head.pitch": 0.0,
        "body.arms.left.upper.pitch": 0.0,
        "body.arms.right.upper.pitch": 0.0
    }

    frame0 = {
        "time": 0,
        "data": neutral_data.copy()
    }


    from_limits = {
      "body.head.yaw": (-0.874, 0.874),
      "body.head.roll": (-0.174, 0.174),
      "body.head.pitch": (-0.174, 0.174),
      "body.arms.left.upper.pitch": (-2.59, 1.59),
      "body.arms.right.upper.pitch": (-2.59, 1.59)
    }

    half_time = duration // 2
    peak_data = {}
    amplitude_factor = 0.2  # up to ±20% of limit

    for joint, (min_val, max_val) in from_limits.items():
        # e.g. amplitude is 20% of the absolute range
        range_ = (max_val - min_val) * amplitude_factor
        rand_angle = random.uniform(-range_, range_) * scale

        # clamp to actual hardware limit
        rand_angle = _clamp(rand_angle, min_val, max_val)

        # round to 3 decimals
        rand_angle = round(rand_angle, 3)
        peak_data[joint] = rand_angle

    frame1 = {
        "time": half_time,
        "data": peak_data
    }

    frame2 = {
        "time": duration,
        "data": neutral_data.copy()
    }

    return [frame0, frame1, frame2]