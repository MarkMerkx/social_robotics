import random

def ease_in_out(t):
    """
    Ease-in-out interpolation function.

    Args:
        t (float): Normalized time (0 <= t <= 1).

    Returns:
        float: Smoothed interpolation value.
    """
    return 3 * t ** 2 - 2 * t ** 3



def smooth_predefined_frames(keyframes, steps=10):
    """
    Smooths a list of predefined keyframes (such as those from a JSON gesture)
    by inserting intermediate frames using ease-in-out interpolation.

    Args:
        keyframes (list): List of keyframe dictionaries with 'time' and 'data'.
        steps (int): Number of intermediate frames to insert between each keyframe pair.

    Returns:
        list: A new list of keyframes including the interpolated frames.
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = start_frame["time"]
        end_time = end_frame["time"]
        delta_time = end_time - start_time

        # Add the starting keyframe (only once for the very first frame)
        if i == 0:
            smoothed_frames.append(start_frame)

        # Generate intermediate frames
        for step in range(1, steps):
            t = step / float(steps)
            t_smooth = ease_in_out(t)
            new_time = start_time + delta_time * t_smooth
            new_data = {}
            for joint, start_val in start_frame["data"].items():
                # Ensure each joint is interpolated; if missing, use start value as default.
                end_val = end_frame["data"].get(joint, start_val)
                new_val = start_val + (end_val - start_val) * t_smooth
                # Optionally, add a very small random perturbation to mimic natural variation.
                new_val += random.uniform(-0.005, 0.005)
                new_data[joint] = new_val
            smoothed_frames.append({"time": new_time, "data": new_data})

        # Append the original end keyframe
        smoothed_frames.append(end_frame)

    return smoothed_frames


def smooth_keyframes(keyframes, steps=10):
    """
    Smooths keyframes by inserting additional frames between each keyframe
    using a specified non-linear interpolation.

    Args:
        keyframes (list): Original keyframes (each a dict with 'time' and 'data').
        steps (int): Number of intermediate frames to insert between each pair.
        interpolation_type (str): Type of interpolation ('ease_in_out', 'cosine', 'linear').

    Returns:
        list: A new list of keyframes including interpolated intermediate frames.
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = start_frame["time"]
        end_time = end_frame["time"]
        delta_time = end_time - start_time

        # Add the starting frame (for the very first keyframe).
        if i == 0:
            smoothed_frames.append(start_frame)

        # Generate intermediate frames.
        for step in range(1, steps):
            t = step / float(steps)
            t_interp = ease_in_out(t)
            new_time = start_time + delta_time * t_interp
            new_data = {}
            # Interpolate each joint value.
            for joint, start_val in start_frame["data"].items():
                end_val = end_frame["data"].get(joint, start_val)
                new_val = start_val + (end_val - start_val) * t_interp
                # Optionally add a small random perturbation.
                new_val += random.uniform(-0.005, 0.005)
                new_data[joint] = new_val
            smoothed_frames.append({"time": new_time, "data": new_data})

        # Append the end keyframe.
        smoothed_frames.append(end_frame)

    return smoothed_frames

