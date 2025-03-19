"""
Image capture module for robot vision.

Provides functionality to capture images from the robot's camera and save them.
"""

import logging
import os
import io
from autobahn.twisted.util import sleep
import time
import shutil
from PIL import Image
from twisted.internet.defer import inlineCallbacks
import numpy as np

logger = logging.getLogger(__name__)

# Constants
SCAN_DIR = "scan_images"


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
        # Flush older frames
        for _ in range(2):  # read 2 times
            _ = yield session.call("rom.sensor.sight.read", time=0)
            yield sleep(0.3)  # short delay between flush calls

        image_data = yield session.call("rom.sensor.sight.read", time=0.5)
        yield sleep(0.3)  # short extra wait, just in case

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

                    # Convert to PIL Image first to check the actual resolution
                    image = Image.open(io.BytesIO(raw_bytes))

                    # If image is smaller than 480x640, resize it to match YOLO's processing resolution
                    if image.width < 480 or image.height < 640:
                        logger.info(f"Original image resolution: {image.width}x{image.height}, resizing to 480x640")
                        # Resize the image to 480x640 while maintaining aspect ratio
                        image = resize_with_padding(image, (480, 640))

                        # Convert the resized image back to bytes for saving
                        buffer = io.BytesIO()
                        image.save(buffer, format="JPEG")
                        buffer.seek(0)
                        resized_bytes = buffer.read()

                        # Save the resized image
                        with open(filename, "wb") as f:
                            f.write(resized_bytes)
                    else:
                        # Save the original image
                        with open(filename, "wb") as f:
                            f.write(raw_bytes)

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


def resize_with_padding(image, target_size):
    """
    Resize image to target size while maintaining aspect ratio and adding padding if necessary.

    :param image: PIL image
    :param target_size: (width, height) tuple
    :return: Resized PIL image
    """
    target_width, target_height = target_size
    width, height = image.size

    # Calculate target ratio and image ratio
    target_ratio = target_width / target_height
    img_ratio = width / height

    # Calculate new dimensions
    if img_ratio > target_ratio:
        # Image is wider than target
        new_width = target_width
        new_height = int(new_width / img_ratio)
    else:
        # Image is taller than target
        new_height = target_height
        new_width = int(new_height * img_ratio)

    # Resize the image
    resized_img = image.resize((new_width, new_height), Image.LANCZOS)

    # Create a new image with the target size and paste the resized image
    new_img = Image.new("RGB", (target_width, target_height), color=(0, 0, 0))

    # Calculate position to paste (center)
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2

    # Paste the resized image onto the new image
    new_img.paste(resized_img, (paste_x, paste_y))

    return new_img