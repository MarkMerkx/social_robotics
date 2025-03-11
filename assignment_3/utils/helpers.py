"""
Helper utilities for robot applications.
"""

import os
import logging
import time

logger = logging.getLogger(__name__)


def setup_logging():
    """
    Set up logging configuration.
    """
    logging.basicConfig(
        format='%(asctime)s %(levelname)-8s %(message)s',
        level=logging.DEBUG,
        datefmt='%H:%M:%S'
    )


def create_directory(directory):
    """
    Create a directory if it doesn't exist.

    :param directory: Path to directory
    :type directory: str
    :return: True if successful
    :rtype: bool
    """
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"Created directory: {directory}")
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {e}")
        return False


def format_object_list(objects_dict):
    """
    Format a list of objects for speech output.

    :param objects_dict: Dictionary of object names and counts
    :type objects_dict: dict
    :return: Formatted text
    :rtype: str
    """
    if not objects_dict:
        return "no objects"

    # Sort by count in descending order
    sorted_objects = sorted(objects_dict.items(), key=lambda x: x[1], reverse=True)

    # Get object names
    object_names = [name for name, count in sorted_objects]

    # Format the output
    if len(object_names) == 1:
        return object_names[0]
    elif len(object_names) == 2:
        return f"{object_names[0]} and {object_names[1]}"
    else:
        return ", ".join(object_names[:-1]) + f", and {object_names[-1]}"


def process_detected_objects(existing_objects, new_objects):
    """
    Process detected objects to update master list with best confidence detections.

    :param existing_objects: Existing dictionary of detected objects
    :type existing_objects: dict
    :param new_objects: New dictionary of detected objects
    :type new_objects: dict
    :return: Updated dictionary of detected objects
    :rtype: dict
    """
    if not new_objects:
        return existing_objects

    result = existing_objects.copy()

    for obj_id, obj_data in new_objects.items():
        # Extract the object name
        obj_name = obj_data['name']

        # Check if we already have this object type
        existing_id = None
        for key in result:
            if isinstance(result[key], dict) and 'name' in result[key] and result[key]['name'] == obj_name:
                existing_id = key
                break

        # If we already have this object type with better confidence, skip
        if existing_id and result[existing_id]['confidence'] >= obj_data['confidence']:
            continue

        # Otherwise, add or update the object
        result[obj_id] = obj_data

    return result