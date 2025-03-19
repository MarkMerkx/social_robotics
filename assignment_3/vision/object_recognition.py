"""
Enhanced Object recognition module for robot vision.

Provides functionality to detect and classify objects in images using YOLO
and ChatGPT Vision API for more advanced object recognition.
"""

import logging
import os
import time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import json
from assignment_3.vision.chatgpt_vision import get_chatgpt_vision_objects
logger = logging.getLogger(__name__)

# Constants
OBJECT_DIR = "detected_objects"
CONFIDENCE_THRESHOLD = 0.4  # Minimum confidence to consider a detection valid
USE_CHATGPT_VISION = True  # Flag to enable/disable ChatGPT Vision API

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


def detect_objects_yolo(image, position_info=None):
    """
    Detect objects in an image using YOLO.

    :param image: The image to analyze
    :type image: PIL.Image
    :param position_info: Information about where the image was captured (yaw, pitch)
    :type position_info: dict or None
    :return: Dictionary of detected objects
    :rtype: dict
    """
    if not YOLO_AVAILABLE or model is None:
        logger.warning("YOLO model not available for object detection")
        return {}

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

                # Add to list of detected names
                if name not in detected_names:
                    detected_names.append(name)

                # Crop and save the object
                cropped = image.crop((x1, y1, x2, y2))
                obj_filename = f"{OBJECT_DIR}/{name}_{i}_{timestamp}.jpg"
                cropped.save(obj_filename)

                # Store object information
                object_id = f"yolo_{name}_{i}"
                detected_objects[object_id] = {
                    'name': name,
                    'confidence': conf,
                    'source': 'yolo',
                    'bbox': (x1, y1, x2, y2),
                    'image_path': obj_filename
                }

                # Add position information if available
                if position_info:
                    detected_objects[object_id]['position'] = position_info

        logger.info(f"YOLO detected {len(detected_objects)} objects with names: {detected_names}")
        return detected_objects

    except Exception as e:
        logger.error(f"Error in YOLO object detection: {e}")
        return {}


def detect_objects(image, position_info=None, use_chatgpt=USE_CHATGPT_VISION, use_yolo=False):
    """
    Detect objects in an image using multiple detection methods.

    :param image: The image to analyze
    :type image: PIL.Image
    :param position_info: Information about where the image was captured (yaw, pitch, position_id, etc.)
    :type position_info: dict or None
    :param use_chatgpt: Whether to use ChatGPT Vision API
    :type use_chatgpt: bool
    :param use_yolo: Whether to use YOLO for object detection
    :type use_yolo: bool
    :return: Dictionary of detected objects and path to annotated image
    :rtype: tuple(dict, str)
    """
    detected_objects = {}
    timestamp = int(time.time())

    # Use YOLO for object detection if enabled
    if use_yolo:
        yolo_objects = detect_objects_yolo(image, position_info)
        detected_objects.update(yolo_objects)
        logger.info(f"YOLO detection completed with {len(yolo_objects)} objects")
    else:
        logger.info("YOLO detection disabled")

    # If enabled and available, use ChatGPT Vision API for additional analysis
    if use_chatgpt:
        try:
            logger.info("Using ChatGPT Vision API for object detection")
            gpt_objects = get_chatgpt_vision_objects(image, position_info)

            # Add position information to GPT objects if available
            if position_info:
                for obj_id, obj_data in gpt_objects.items():
                    # Copy all position information
                    for key, value in position_info.items():
                        if key not in obj_data:
                            obj_data[key] = value

            # Merge with existing detections
            detected_objects.update(gpt_objects)
            logger.info(f"ChatGPT Vision detection completed with {len(gpt_objects)} objects")
        except Exception as e:
            logger.error(f"Error in ChatGPT Vision object detection: {e}")

    # Create annotated image from the detections
    annotated_img, annotated_filename = create_annotated_image(image, detected_objects, timestamp, position_info)

    return detected_objects, annotated_filename


def create_annotated_image(image, detected_objects, timestamp, position_info=None):
    """
    Create an annotated image with bounding boxes for detected objects.

    :param image: The original image
    :type image: PIL.Image
    :param detected_objects: Detected objects dictionary
    :type detected_objects: dict
    :param timestamp: Timestamp for filename
    :type timestamp: int
    :param position_info: Information about where the image was captured
    :type position_info: dict or None
    :return: Annotated image and filename
    :rtype: tuple(PIL.Image, str)
    """
    # Create a copy for annotations
    annotated_img = image.copy()
    draw = ImageDraw.Draw(annotated_img)

    # Try to get a font
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        font = ImageFont.load_default()

    detected_names = []

    # Draw annotations for each object
    for obj_id, obj_data in detected_objects.items():
        name = obj_data['name']
        confidence = obj_data['confidence']
        source = obj_data.get('source', 'unknown')

        # Add to list of detected names for filename
        if name not in detected_names:
            detected_names.append(name)

        # If object has a bounding box, draw it
        if 'bbox' in obj_data:
            x1, y1, x2, y2 = obj_data['bbox']

            # Different colors for different sources
            outline_color = "red" if source == 'yolo' else "blue"

            # Draw bounding box
            draw.rectangle([x1, y1, x2, y2], outline=outline_color, width=2)

            # Draw label
            label = f"{name}: {confidence:.2f} ({source})"
            draw.text((x1, y1 - 10), label, fill=outline_color, font=font)
        else:
            # For objects without bounding boxes (like from ChatGPT), add a note at the top
            y_pos = 10 + detected_names.index(name) * 20
            label = f"{name}: {confidence:.2f} ({source})"
            draw.text((10, y_pos), label, fill="blue", font=font)

    # Get position identifier if available
    position_id = ""
    if position_info:
        # Check for position_id directly
        if 'position_id' in position_info:
            position_id = position_info['position_id']
        # Alternatively construct from orientation and turn
        elif 'orientation' in position_info and 'turn' in position_info:
            position_id = f"{position_info['turn']}_{position_info['orientation']}"

    # Create filename with position and detected objects (first 3)
    object_names = "_".join(detected_names[:3]) if detected_names else "none"

    # Include position_id in filename if available
    if position_id:
        annotated_filename = f"scan_images/pos_{position_id}_{object_names}_{timestamp}.jpg"
    else:
        annotated_filename = f"scan_images/annotated_{object_names}_{timestamp}.jpg"

    # Save annotated image
    os.makedirs("scan_images", exist_ok=True)
    annotated_img.save(annotated_filename)
    logger.info(f"Annotated image saved as '{annotated_filename}' with {len(detected_objects)} objects")

    return annotated_img, annotated_filename


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
        source = obj_data.get('source', 'unknown')

        # Check if we already have this object by name and source
        existing_id = None
        for existing_key in existing_objects:
            existing_data = existing_objects[existing_key]
            if (existing_data['name'] == name and
                existing_data.get('source', 'unknown') == source):
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


def save_detection_results(detected_objects, filename="detection_results.json"):
    """
    Save detection results to a JSON file for further analysis.

    :param detected_objects: Dictionary of detected objects
    :type detected_objects: dict
    :param filename: Output filename
    :type filename: str
    """
    # Create a serializable copy of the results
    serializable_results = {}

    for obj_id, obj_data in detected_objects.items():
        # Create a copy of the object data
        obj_copy = obj_data.copy()

        # Convert non-serializable data types
        if 'bbox' in obj_copy:
            obj_copy['bbox'] = list(obj_copy['bbox'])

        # Remove any image data that's not serializable
        if 'image_data' in obj_copy:
            del obj_copy['image_data']

        serializable_results[obj_id] = obj_copy

    # Save to file
    with open(filename, 'w') as f:
        json.dump(serializable_results, f, indent=2)

    logger.info(f"Detection results saved to {filename}")

