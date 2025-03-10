# assignment_3/vision/scanning.py
"""
Object scanning and recognition module for the I Spy game.
Uses predefined gestures from the gestures.json library for scanning movements.
"""

import logging
import os
import time
import base64
import io
import math
import random
from PIL import Image, ImageDraw
import numpy as np
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from ultralytics import YOLO

# Import gesture handling
from ..gesture_control.scanning_gestures import (
    perform_scan_gesture,
    perform_scan_360,
    perform_look_up_down,
    perform_point_to,
    perform_thinking_gesture,
    perform_attention_gesture,
    perform_scan_with_callback
)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants for scanning
ROTATION_ANGLE_DEGREES = 30  # How many degrees to turn between captures
FULL_ROTATION = 360  # Full rotation in degrees
SCAN_HEIGHT_ANGLES = [0, 15, -15]  # Scan at eye level, looking up, and looking down

# Initialize YOLO model
try:
    # Use YOLOv8n if v11 is not available - adapt as needed
    model = YOLO("yolov8n.pt")  # Load YOLOv8 nano model for faster inference
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load YOLO model: {e}")
    model = None


class ObjectScanner:
    def __init__(self, session):
        self.session = session
        self.detected_objects = {}  # Dictionary to store detected objects
        self.current_angle = 0  # Track the current head angle
        self.image_buffer = []  # Store captured images
        self.debug_mode = True  # Set to True to enable debug modal

    @inlineCallbacks
    def perform_full_scan(self, scan_angles=None):
        """
        Perform a full scan, taking pictures at specified intervals.
        Uses predefined gestures for movement.

        Args:
            scan_angles: Optional list of horizontal angles to scan at.
                         If None, performs a full 360-degree scan.
        """
        logger.info("Starting environmental scan")

        # Clear previous scan results
        self.detected_objects = {}
        self.image_buffer = []

        # Make a scanning gesture to indicate the robot is about to scan
        yield perform_scan_gesture(self.session)

        # Use scan_with_callback to perform the scanning
        yield perform_scan_with_callback(
            self.session,
            self._capture_and_analyze_callback,
            increment=ROTATION_ANGLE_DEGREES,
            count=int(FULL_ROTATION / ROTATION_ANGLE_DEGREES)
        )

        logger.info(f"Scan complete. Detected {len(self.detected_objects)} unique objects.")
        return self.detected_objects

    @inlineCallbacks
    def _capture_and_analyze_callback(self, angle, pitch):
        """
        Callback function for perform_scan_with_callback.
        Captures and analyzes an image at the current position.

        Args:
            angle: Current yaw angle in degrees
            pitch: Current pitch angle in degrees
        """
        try:
            # Capture an image from the robot's camera
            image_data = yield self.session.call("rom.sensor.sight.read", time=0.0)

            if not image_data:
                logger.warning(f"Failed to capture image at angle={angle}°, pitch={pitch}°: No data received")
                return

            # Convert raw image data to a format suitable for YOLO
            image = self._decode_image(image_data)

            if image is None:
                logger.warning(f"Failed to decode image at angle={angle}°, pitch={pitch}°")
                return

            # Add the image to our buffer for debug purposes
            self.image_buffer.append(image.copy())

            # Process the image with YOLO
            detected_objects = self._detect_objects(image)

            # Update the detected objects with position information
            self._update_detected_objects(detected_objects, angle, pitch)

            logger.info(f"Processed image at angle={angle}°, pitch={pitch}°: Found {len(detected_objects)} objects")

        except Exception as e:
            logger.error(f"Error in capture_and_analyze_callback: {e}")

    @inlineCallbacks
    def _capture_and_analyze(self):
        """Capture an image and analyze it with YOLO."""
        try:
            # Capture an image from the robot's camera
            image_data = yield self.session.call("rom.sensor.sight.read", time=0.0)

            if not image_data:
                logger.warning("Failed to capture image: No data received")
                return {}

            # Convert raw image data to a format suitable for YOLO
            image = self._decode_image(image_data)

            if image is None:
                logger.warning("Failed to decode image")
                return {}

            # Add the image to our buffer for debug purposes
            self.image_buffer.append(image.copy())

            # Process the image with YOLO
            detected_objects = self._detect_objects(image)

            return detected_objects

        except Exception as e:
            logger.error(f"Error in capture_and_analyze: {e}")
            return {}

    def _decode_image(self, image_data):
        """Convert raw image data from the robot to a PIL Image."""
        try:
            # Extract raw image bytes (may need adjustment based on actual format)
            if isinstance(image_data, dict) and 'data' in image_data:
                raw_bytes = base64.b64decode(image_data['data'])
            elif isinstance(image_data, bytes):
                raw_bytes = image_data
            else:
                logger.warning(f"Unexpected image data format: {type(image_data)}")
                return None

            # Convert to PIL Image
            image = Image.open(io.BytesIO(raw_bytes))
            return image

        except Exception as e:
            logger.error(f"Error decoding image: {e}")
            return None

    def _detect_objects(self, image):
        """Use YOLO to detect objects in the image."""
        if model is None:
            logger.error("YOLO model not initialized")
            return {}

        try:
            # Convert PIL image to numpy array for YOLO
            img_array = np.array(image)

            # Run YOLO inference
            results = model(img_array)

            # Process and format the results
            detected_objects = {}
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = box.xyxy[0].tolist()  # Bounding box coordinates
                    conf = float(box.conf[0])  # Confidence score
                    cls = int(box.cls[0])  # Class ID
                    name = model.names[cls]  # Class name

                    # Only keep objects with confidence above threshold
                    if conf < 0.4:
                        continue

                    # Store the detection with highest confidence
                    if name not in detected_objects or detected_objects[name]['confidence'] < conf:
                        # Create a cropped version of the object
                        cropped = image.crop((x1, y1, x2, y2))

                        # Convert the cropped image to base64 for storage/display
                        buffered = io.BytesIO()
                        cropped.save(buffered, format="JPEG")
                        img_str = base64.b64encode(buffered.getvalue()).decode()

                        # Extract color information
                        color = self._extract_dominant_color(cropped)

                        detected_objects[name] = {
                            'confidence': conf,
                            'bbox': (x1, y1, x2, y2),
                            'image': img_str,
                            'color': color
                        }

            logger.info(f"Detected {len(detected_objects)} objects in image")
            return detected_objects

        except Exception as e:
            logger.error(f"Error in object detection: {e}")
            return {}

    def _extract_dominant_color(self, image):
        """Extract the dominant color from an image."""
        try:
            # Resize image to speed up processing
            img = image.copy()
            img.thumbnail((100, 100))

            # Convert to RGB if not already
            if img.mode != "RGB":
                img = img.convert("RGB")

            # Get colors from image
            colors = img.getcolors(10000)

            # Sort by count and get the most common
            colors.sort(reverse=True, key=lambda x: x[0])

            # Map RGB to color names
            r, g, b = colors[0][1]

            # Simple color classification
            color_map = {
                'red': (255, 0, 0),
                'green': (0, 255, 0),
                'blue': (0, 0, 255),
                'yellow': (255, 255, 0),
                'cyan': (0, 255, 255),
                'magenta': (255, 0, 255),
                'black': (0, 0, 0),
                'white': (255, 255, 255),
                'gray': (128, 128, 128),
                'orange': (255, 165, 0),
                'brown': (165, 42, 42),
                'purple': (128, 0, 128),
                'pink': (255, 192, 203)
            }

            # Find closest color by Euclidean distance
            min_dist = float('inf')
            closest_color = 'unknown'

            for color_name, color_rgb in color_map.items():
                dist = sum((c1 - c2) ** 2 for c1, c2 in zip((r, g, b), color_rgb))
                if dist < min_dist:
                    min_dist = dist
                    closest_color = color_name

            return closest_color
        except Exception as e:
            logger.error(f"Error extracting color: {e}")
            return "unknown"

    def _update_detected_objects(self, new_objects, angle, pitch):
        """Update the master list of detected objects with new detections."""
        for name, data in new_objects.items():
            # Only update if this is a new object or has higher confidence
            if name not in self.detected_objects or data['confidence'] > self.detected_objects[name]['confidence']:
                # Add positional information
                data['position'] = {
                    'angle': angle,
                    'pitch': pitch
                }
                self.detected_objects[name] = data

    @inlineCallbacks
    def _reset_head_position(self):
        """Reset the robot's head to the default position."""
        try:
            # Reset head position (yaw, roll, pitch to 0)
            yield self.session.call("rom.motion.joint.move", joint="body.head.yaw", angle=0.0, speed=0.5)
            yield self.session.call("rom.motion.joint.move", joint="body.head.roll", angle=0.0, speed=0.5)
            yield self.session.call("rom.motion.joint.move", joint="body.head.pitch", angle=0.0, speed=0.5)
            self.current_angle = 0
            logger.debug("Head position reset to default")
        except Exception as e:
            logger.error(f"Error resetting head position: {e}")

    @inlineCallbacks
    def point_to_object(self, object_name):
        """
        Make the robot point toward a detected object using predefined pointing gestures.

        Args:
            object_name: Name of the object to point to

        Returns:
            True if successful, False otherwise
        """
        # Find the object in our detected list (case-insensitive)
        object_name_lower = object_name.lower()
        matching_objects = [obj for obj in self.detected_objects.keys()
                            if obj.lower() == object_name_lower]

        if not matching_objects:
            logger.warning(f"Cannot point to '{object_name}': Object not detected")
            return False

        # Use the first matching object
        object_key = matching_objects[0]
        object_data = self.detected_objects[object_key]

        try:
            # Get the angle where the object was detected
            if 'position' in object_data:
                angle_to_object = object_data['position']['angle']
                pitch_angle = object_data['position']['pitch']
            else:
                # If no position data, use current or default angles
                angle_to_object = self.current_angle
                pitch_angle = 0

            # Use the point_to gesture function
            yield perform_point_to(self.session, angle_to_object)

            logger.info(f"Robot is now pointing at '{object_name}'")
            return True

        except Exception as e:
            logger.error(f"Error pointing to object: {e}")
            return False

    def get_object_info(self, object_name):
        """
        Get information about a detected object.

        Args:
            object_name: Name of the object

        Returns:
            Dictionary with object properties or None if not found
        """
        object_name_lower = object_name.lower()
        for obj_name, data in self.detected_objects.items():
            if obj_name.lower() == object_name_lower:
                return {
                    'name': obj_name,
                    'confidence': data['confidence'],
                    'color': data.get('color', 'unknown'),
                    'position': data.get('position', {})
                }
        return None

    def get_random_object(self, exclude_objects=None):
        """
        Get a random object from detected objects.

        Args:
            exclude_objects: List of object names to exclude

        Returns:
            Tuple of (object_name, object_data) or (None, None) if no objects available
        """
        if not self.detected_objects:
            return None, None

        available_objects = list(self.detected_objects.keys())

        # Filter out excluded objects
        if exclude_objects:
            available_objects = [obj for obj in available_objects if obj not in exclude_objects]

        if not available_objects:
            return None, None

        # Select a random object
        selected_object = random.choice(available_objects)
        return selected_object, self.detected_objects[selected_object]