"""
Object recognition module for robot vision.

Provides functionality to detect and classify objects in images using YOLO.
"""

import logging
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

# Constants
OBJECT_DIR = "detected_objects"
CONFIDENCE_THRESHOLD = 0.4  # Minimum confidence to consider a detection valid

# Initialize YOLO model
try:
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")  # Load YOLOv8 nano model (lightweight)
    YOLO_AVAILABLE = True
    logger.info("YOLO model loaded successfully")
except Exception as e:
    logger.error(f"Failed to load YOLO model: {e}")
    YOLO_AVAILABLE = False
    model = None


def initialize_object_directory():
    """
    Initialize the directory for storing detected objects.

    :return: Path to the object directory
    :rtype: str
    """
    if not os.path.exists(OBJECT_DIR):
        os.makedirs(OBJECT_DIR)
    logger.info(f"Initialized object directory: {OBJECT_DIR}")
    return OBJECT_DIR


def detect_objects(image, position_info=None):
    """
    Detect objects in an image using YOLO.

    :param image: The image to analyze
    :type image: PIL.Image
    :param position_info: Information about where the image was captured (yaw, pitch)
    :type position_info: dict or None
    :return: Dictionary of detected objects and path to annotated image
    :rtype: tuple(dict, str)
    """
    if not YOLO_AVAILABLE or model is None:
        logger.warning("YOLO model not available for object detection")
        return {}, None

    try:
        # Convert PIL image to numpy array for YOLO
        img_array = np.array(image)

        # Run YOLO inference
        results = model(img_array)

        # Get timestamp for filenames
        timestamp = int(time.time())

        # Process each detection
        detected_objects = {}
        detected_names = []

        # Create a copy for annotations
        annotated_img = image.copy()
        draw = ImageDraw.Draw(annotated_img)

        # Try to get a font
        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        # Process each detection
        for r in results:
            boxes = r.boxes
            for i, box in enumerate(boxes):
                x1, y1, x2, y2 = box.xyxy[0].tolist()  # Bounding box coordinates
                conf = float(box.conf[0])  # Confidence score
                cls = int(box.cls[0])  # Class ID
                name = model.names[cls]  # Class name

                # Skip low confidence detections
                if conf < CONFIDENCE_THRESHOLD:
                    continue

                # Add to list of detected names for filename
                if name not in detected_names:
                    detected_names.append(name)

                # Draw bounding box
                draw.rectangle([x1, y1, x2, y2], outline="red", width=2)

                # Draw label
                label = f"{name}: {conf:.2f}"
                draw.text((x1, y1 - 10), label, fill="red", font=font)

                # Crop and save the object
                cropped = image.crop((x1, y1, x2, y2))
                obj_filename = f"{OBJECT_DIR}/{name}_{i}_{timestamp}.jpg"
                cropped.save(obj_filename)

                # Store object information
                object_id = f"{name}_{i}"
                detected_objects[object_id] = {
                    'name': name,
                    'confidence': conf,
                    'bbox': (x1, y1, x2, y2),
                    'image_path': obj_filename
                }

                # Add position information if available
                if position_info:
                    detected_objects[object_id]['position'] = position_info

        # Create filename with detected objects (first 3)
        object_names = "_".join(detected_names[:3]) if detected_names else "none"
        annotated_filename = f"scan_images/annotated_{object_names}_{timestamp}.jpg"

        # Save annotated image
        annotated_img.save(annotated_filename)
        logger.info(f"Annotated image saved as '{annotated_filename}' with {len(detected_objects)} objects")

        return detected_objects, annotated_filename

    except Exception as e:
        logger.error(f"Error in object detection: {e}")
        return {}, None


def merge_detections(existing_objects, new_objects):
    """
    Merge new object detections with existing ones, keeping the highest confidence detections.

    :param existing_objects: Dictionary of existing object detections
    :type existing_objects: dict
    :param new_objects: Dictionary of new object detections
    :type new_objects: dict
    :return: Updated objects dictionary
    :rtype: dict
    """
    for obj_id, obj_data in new_objects.items():
        # Extract the object name without the index
        name = obj_data['name']

        # Check if we already have this object by name
        existing_id = None
        for existing_key in existing_objects:
            if existing_objects[existing_key]['name'] == name:
                existing_id = existing_key
                break

        # If object exists, keep the one with higher confidence
        if existing_id and existing_objects[existing_id]['confidence'] >= obj_data['confidence']:
            continue

        # Add or update the object
        existing_objects[obj_id] = obj_data

    return existing_objects


def get_unique_objects(detected_objects):
    """
    Get a list of unique object names from detected objects.

    :param detected_objects: Dictionary of detected objects
    :type detected_objects: dict
    :return: Dictionary of unique object names and their counts
    :rtype: dict
    """
    unique_objects = {}
    for obj_key, obj_data in detected_objects.items():
        object_name = obj_data['name']
        if object_name not in unique_objects:
            unique_objects[object_name] = 1
        else:
            unique_objects[object_name] += 1

    return unique_objects