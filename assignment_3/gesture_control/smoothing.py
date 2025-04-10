# /gesture_control/smoothing.py
import random

"""
Smoothing functionality is currently disabled due to microstops observed in the robot's motion.
The ease-in-out interpolation and frame generation logic remains implemented but may require
adjustments to address the microstop issue.
"""

def ease_in_out(t):
    """
    Ease-in-out interpolation function producing an S-curve.

    :param float t: Interpolation parameter between 0 and 1
    :return: Smoothed interpolation value
    :rtype: float
    """
    return 3 * (t ** 2) - 2 * (t ** 3)


def smooth_predefined_frames(keyframes, steps=2):
    """
    Smooths a list of predefined keyframes by inserting intermediate frames using ease-in-out interpolation.

    :param list keyframes: List of dictionaries with "time" (float) and "data" (dict of joint angles)
    :param int steps: Number of segments between original frames (steps=2 inserts 1 frame per pair)
    :return: List of smoothed frames with times and angles rounded to 3 decimal places
    :rtype: list
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = float(start_frame["time"])
        end_time = float(end_frame["time"])
        delta_time = end_time - start_time

        if i == 0:
            smoothed_frames.append({
                "time": round(start_time, 3),
                "data": {j: round(a, 3) for j, a in start_frame["data"].items()}
            })

        for step_i in range(1, steps):
            t = step_i / float(steps)
            t_smooth = ease_in_out(t)
            new_time = start_time + delta_time * t_smooth
            new_time = round(new_time, 3)

            new_data = {}
            for joint, start_val in start_frame["data"].items():
                end_val = end_frame["data"].get(joint, start_val)
                val = start_val + (end_val - start_val) * t_smooth
                val += random.uniform(-0.005, 0.005)
                val = round(val, 3)
                new_data[joint] = val

            smoothed_frames.append({
                "time": new_time,
                "data": new_data
            })

        smoothed_frames.append({
            "time": round(end_time, 3),
            "data": {j: round(a, 3) for j, a in end_frame["data"].items()}
        })

    return smoothed_frames


def smooth_keyframes(keyframes, steps=1):
    """
    Smooths keyframes with ease-in-out interpolation for general usage (e.g., generated beat frames).

    :param list keyframes: List of dictionaries with "time" (float) and "data" (dict of joint angles)
    :param int steps: Number of segments between frames (steps=1 inserts no new frames)
    :return: List of smoothed frames with times and angles rounded to 3 decimal places
    :rtype: list
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = float(start_frame["time"])
        end_time = float(end_frame["time"])
        delta_time = end_time - start_time

        if i == 0:
            smoothed_frames.append({
                "time": round(start_time, 3),
                "data": {j: round(a, 3) for j, a in start_frame["data"].items()}
            })

        for step_i in range(1, steps):
            t = step_i / float(steps)
            t_smooth = ease_in_out(t)
            new_time = start_time + delta_time * t_smooth
            new_time = round(new_time, 3)

            new_data = {}
            for joint, start_val in start_frame["data"].items():
                end_val = end_frame["data"].get(joint, start_val)
                val = start_val + (end_val - start_val) * t_smooth
                val += random.uniform(-0.005, 0.005)
                val = round(val, 3)
                new_data[joint] = val

            smoothed_frames.append({
                "time": new_time,
                "data": new_data
            })

        smoothed_frames.append({
            "time": round(end_time, 3),
            "data": {j: round(a, 3) for j, a in end_frame["data"].items()}
        })

    return smoothed_frames