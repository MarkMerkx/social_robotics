"""
Image capture module for robot vision.

Provides functionality to capture images from the robot's camera and save them.
"""

import logging
import os
import io
import time
import shutil
from PIL import Image
from twisted.internet.defer import inlineCallbacks

logger = logging.getLogger(__name__)

# Constants
SCAN_DIR = "scan_images"

# Camera resolution settings - we attempt these but the robot may have fixed resolution
CAMERA_WIDTH = 1280  # Request higher resolution
CAMERA_HEIGHT = 720  # HD resolution
CAMERA_QUALITY = 90  # Higher quality (0-100)


def initialize_image_directory():
    """
    Initialize the image directory by clearing old images and creating if needed.

    :return: Path to the image directory
    :rtype: str
    """
    # Remove existing directory and recreate it
    if os.path.exists(SCAN_DIR):
        shutil.rmtree(SCAN_DIR)
    os.makedirs(SCAN_DIR)
    logger.info(f"Initialized image directory: {SCAN_DIR}")
    return SCAN_DIR


@inlineCallbacks
def capture_image(session, yaw=None, pitch=None):
    """
    Capture an image from the robot's camera.

    :param session: The WAMP session
    :type session: Component
    :param yaw: Current yaw angle if known
    :type yaw: float
    :param pitch: Current pitch angle if known
    :type pitch: float
    :return: Captured image and save path, or None if failed
    :rtype: tuple(Image, str) or None
    """
    try:
        logger.info("Capturing image...")

        # Just use default parameters - high resolution request didn't work
        image_data = yield session.call("rom.sensor.sight.read", time=0.0)

        if not image_data:
            logger.warning("No image data received")
            return None

        # Process the nested data structure
        if isinstance(image_data, list) and len(image_data) > 0:
            if isinstance(image_data[0], dict) and 'data' in image_data[0]:
                data_dict = image_data[0]['data']

                if isinstance(data_dict, dict) and 'body.head.eyes' in data_dict:
                    raw_bytes = data_dict['body.head.eyes']

                    # Generate a timestamped filename with position if available
                    timestamp = int(time.time())
                    position_info = ""
                    if yaw is not None and pitch is not None:
                        position_info = f"_yaw{yaw:.2f}_pitch{pitch:.2f}"

                    filename = f"{SCAN_DIR}/image{position_info}_{timestamp}.jpg"

                    # Save the image
                    with open(filename, "wb") as f:
                        f.write(raw_bytes)

                    # Convert to PIL Image
                    image = Image.open(io.BytesIO(raw_bytes))

                    # Log resolution for debugging
                    logger.info(f"Image saved to {filename} (Resolution: {image.width}x{image.height})")

                    return image, filename
                else:
                    logger.warning("Expected key 'body.head.eyes' not found in data dictionary")
            else:
                logger.warning("Image data doesn't contain 'data' field or isn't a dictionary")
        else:
            logger.warning("Image data is not a list or is empty")

        return None
    except Exception as e:
        logger.error(f"Error capturing image: {e}")
        return None