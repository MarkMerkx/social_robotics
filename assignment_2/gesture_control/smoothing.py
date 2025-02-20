import random


def ease_in_out(t):
    """
    Ease-in-out interpolation function:
    Produces an S-curve from t=0 to t=1.
    """
    return 3 * (t ** 2) - 2 * (t ** 3)


def smooth_predefined_frames(keyframes, steps=2):
    """
    Smooths a list of predefined keyframes by inserting intermediate frames
    using ease-in-out interpolation.

    - Keeps time as a float (rounded to 3 decimals).
    - Rounds angles to 3 decimals.
    - steps=2 => inserts 1 interpolated frame per pair. Increase for more intermediate frames.

    Args:
        keyframes (list): A list of dicts: {"time": ..., "data": {...}}
        steps (int): Number of segments between original frames (n frames => n-1 segments).

    Returns:
        list: new list of frames with times (floats) and angles at 3-decimal precision.
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = float(start_frame["time"])
        end_time = float(end_frame["time"])
        delta_time = end_time - start_time

        # Add the starting keyframe for the first pair.
        if i == 0:
            smoothed_frames.append({
                "time": round(start_time, 3),
                "data": {j: round(a, 3) for j, a in start_frame["data"].items()}
            })

        # Generate intermediate frames
        for step_i in range(1, steps):
            t = step_i / float(steps)
            t_smooth = ease_in_out(t)
            new_time = start_time + delta_time * t_smooth
            new_time = round(new_time, 3)  # keep as float, just 3-decimal rounding

            new_data = {}
            for joint, start_val in start_frame["data"].items():
                end_val = end_frame["data"].get(joint, start_val)
                val = start_val + (end_val - start_val) * t_smooth
                # Optionally add a small random perturbation:
                val += random.uniform(-0.005, 0.005)
                val = round(val, 3)
                new_data[joint] = val

            smoothed_frames.append({
                "time": new_time,
                "data": new_data
            })

        # Append the original end keyframe, rounding to 3 decimals
        smoothed_frames.append({
            "time": round(end_time, 3),
            "data": {
                j: round(a, 3) for j, a in end_frame["data"].items()
            }
        })

    return smoothed_frames


def smooth_keyframes(keyframes, steps=1):
    """
    Similar to smooth_predefined_frames, but for general usage
    (e.g., generated beat frames).

    - Keeps time as float, rounding to 3 decimals.
    - steps=1 means no new frames are inserted.
      Increase steps if you want more interpolation frames.
    """
    smoothed_frames = []

    for i in range(len(keyframes) - 1):
        start_frame = keyframes[i]
        end_frame = keyframes[i + 1]
        start_time = float(start_frame["time"])
        end_time = float(end_frame["time"])
        delta_time = end_time - start_time

        # Add the starting frame for the first segment.
        if i == 0:
            smoothed_frames.append({
                "time": round(start_time, 3),
                "data": {j: round(a, 3) for j, a in start_frame["data"].items()}
            })

        # Generate intermediate frames
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

        # Append the end frame (rounded)
        smoothed_frames.append({
            "time": round(end_time, 3),
            "data": {
                j: round(a, 3) for j, a in end_frame["data"].items()
            }
        })

    return smoothed_frames
