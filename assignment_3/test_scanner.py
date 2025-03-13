"""
Test scanner for the robot vision system.

Tests the object scanning and recognition functionality with options for
both static field of view and 360-degree scanning modes.
"""

from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
import logging
import os
import argparse

# Import modules
from vision.image_capture import initialize_image_directory, capture_image
from vision.object_recognition import initialize_object_directory, detect_objects, get_unique_objects, save_detection_results
from gesture_control.scanning import (
    perform_scan,
    point_to_object,
    MODE_STATIC,
    MODE_360
)
from utils.helpers import setup_logging, format_object_list, process_detected_objects

# Create directories for modules if they don't exist
os.makedirs("vision", exist_ok=True)
os.makedirs("gesture_control", exist_ok=True)
os.makedirs("utils", exist_ok=True)

# Create __init__.py files to ensure imports work
for directory in ["vision", "gesture_control", "utils"]:
    init_file = os.path.join(directory, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            pass

# Set up logging
setup_logging()
logger = logging.getLogger(__name__)

# Create output directories
initialize_image_directory()
initialize_object_directory()


@inlineCallbacks
def capture_and_analyze(session, yaw, pitch, **kwargs):
    """
    Capture an image at the given position and analyze it for objects.

    :param session: The WAMP session
    :type session: Component
    :param yaw: Yaw angle in radians
    :type yaw: float
    :param pitch: Pitch angle in radians
    :type pitch: float
    :return: Dictionary of detected objects
    :rtype: dict
    """
    try:
        # Capture image
        result = yield capture_image(session, yaw, pitch)

        if not result:
            logger.warning("Failed to capture image")
            return {}

        image, _ = result

        # Create comprehensive position info for the I Spy game
        position_info = {
            'yaw': yaw,
            'pitch': pitch,
            'turn': kwargs.get('turn', 0),
            'cumulative_rotation': kwargs.get('cumulative_rotation', 0),
            'orientation': kwargs.get('orientation', 'middle'),
            'position_id': kwargs.get('position_id', f"{kwargs.get('turn', 0)}_{kwargs.get('orientation', 'middle')}")
        }

        # For I Spy game, we primarily want to use ChatGPT Vision for better feature detection
        use_chatgpt = True

        # Detect objects in the image with position info
        objects, annotated_path = detect_objects(image, position_info=position_info, use_chatgpt=use_chatgpt)

        return objects

    except Exception as e:
        logger.error(f"Error in capture_and_analyze: {e}")
        return {}


@inlineCallbacks
def test_single_image(session, use_chatgpt=True):
    """
    Test capturing and analyzing a single image.

    :param session: The WAMP session
    :type session: Component
    :param use_chatgpt: Whether to use ChatGPT Vision API for enhanced detection
    :type use_chatgpt: bool
    :return: Success flag
    :rtype: bool
    """
    logger.info("Testing single image capture and analysis")

    # Whether ChatGPT Vision API should be used
    chatgpt_status = "enabled" if use_chatgpt else "disabled"
    logger.info(f"ChatGPT Vision API is {chatgpt_status} for this test")

    # Capture image
    result = yield capture_image(session)
    if result:
        image, filename = result
        logger.info(f"Captured test image: {filename}")

        # Detect objects with optional ChatGPT Vision API
        objects, annotated_path = detect_objects(image, use_chatgpt=use_chatgpt)

        if objects:
            logger.info(f"Detected {len(objects)} objects in test image")

            # Group objects by source for better reporting
            yolo_objects = [obj for obj_id, obj in objects.items()
                            if obj.get('source', '') == 'yolo']

            gpt_objects = [obj for obj_id, obj in objects.items()
                           if obj.get('source', '') == 'chatgpt']

            # Log YOLO detections
            if yolo_objects:
                logger.info(f"YOLO detected {len(yolo_objects)} objects:")
                for obj in yolo_objects:
                    logger.info(f"  {obj['name']} (confidence: {obj['confidence']:.2f})")

            # Log ChatGPT Vision detections
            if gpt_objects:
                logger.info(f"ChatGPT Vision detected {len(gpt_objects)} objects:")
                for obj in gpt_objects:
                    desc = obj.get('description', 'No description')
                    logger.info(f"  {obj['name']} (confidence: {obj['confidence']:.2f})")
                    logger.info(f"    Description: {desc}")

            # Save detection results to file for detailed analysis
            save_detection_results(objects)

            # Show comparison message if both methods were used
            if yolo_objects and gpt_objects:
                logger.info(f"Comparison: YOLO found {len(yolo_objects)} objects, ChatGPT found {len(gpt_objects)}")

                # Find objects detected by both methods
                yolo_names = set(obj['name'].lower() for obj in yolo_objects)
                gpt_names = set(obj['name'].lower() for obj in gpt_objects)
                common_names = yolo_names.intersection(gpt_names)

                if common_names:
                    logger.info(f"Both methods detected: {', '.join(common_names)}")

                # Find unique detections
                yolo_unique = yolo_names - gpt_names
                gpt_unique = gpt_names - yolo_names

                if yolo_unique:
                    logger.info(f"Only YOLO detected: {', '.join(yolo_unique)}")

                if gpt_unique:
                    logger.info(f"Only ChatGPT detected: {', '.join(gpt_unique)}")
        else:
            logger.info("No objects detected in test image")

        return True
    else:
        logger.warning("Failed to capture test image")
        return False


@inlineCallbacks
def run_scan_test(session, scan_mode=MODE_STATIC, point_enabled=True, difficulty=1):
    """
    Run a complete scan test with the specified mode and select an object for the I Spy game.

    :param session: The WAMP session
    :type session: Component
    :param scan_mode: Scan mode ("static" or "360")
    :type scan_mode: str
    :param point_enabled: Whether to point to detected objects
    :type point_enabled: bool
    :param difficulty: Difficulty level for object selection (1-3)
    :type difficulty: int
    :return: Dictionary with scan results and selected object
    :rtype: dict
    """
    mode_name = "360-degree" if scan_mode == MODE_360 else "static"
    logger.info(f"Starting {mode_name} scan test")

    # Announce start of scan
    yield session.call("rie.dialogue.say", text=f"Starting {mode_name} environment scan")

    # Perform the scan using the capture_and_analyze function
    scan_results, all_objects = yield perform_scan(
        session,
        mode=scan_mode,
        capture_callback=capture_and_analyze,
        process_callback=process_detected_objects
    )

    # Get unique objects for reporting
    unique_objects = get_unique_objects(all_objects)
    object_count = len(unique_objects)

    # Report results
    if object_count > 0:
        formatted_objects = format_object_list(unique_objects)
        result_text = f"I found {object_count} different objects including {formatted_objects}"
        logger.info(f"Scan complete. {result_text}")
        yield session.call("rie.dialogue.say", text=result_text)

        # Select an object for the I Spy game based on difficulty
        from assignment_3.api.api_handler import choose_object

        selected_object = choose_object(all_objects, difficulty)

        if selected_object:
            logger.info(
                f"Selected object for I Spy game: {selected_object['name']} ({selected_object.get('dutch_name', 'unknown')})")
            logger.info(f"Object features: {selected_object.get('features', {})}")
            logger.info(f"Object position: {selected_object.get('position_id', 'unknown')}")

            # Start the I Spy game (this will be handled by another module)
            yield session.call("rie.dialogue.say", text=f"Let's play I Spy! I'm thinking of something in this room.")

            # Store the selected object for the game logic
            game_object = {
                "name": selected_object['name'],
                "dutch_name": selected_object.get('dutch_name', ''),
                "features": selected_object.get('features', {}),
                "position_id": selected_object.get('position_id', ''),
                "orientation": selected_object.get('orientation', ''),
                "turn": selected_object.get('turn', 0),
                "yaw": selected_object.get('yaw', 0),
                "pitch": selected_object.get('pitch', 0),
                "cumulative_rotation": selected_object.get('cumulative_rotation', 0)
            }

            # Save the game object to a file for later use
            try:
                with open('current_game_object.json', 'w') as f:
                    json.dump(game_object, f, indent=2)
                logger.info("Saved game object to current_game_object.json")
            except Exception as e:
                logger.error(f"Error saving game object: {e}")
        else:
            logger.warning("Failed to select an object for the I Spy game")
    else:
        logger.info("Scan complete. No objects detected.")
        yield session.call("rie.dialogue.say", text="Scan complete. I didn't detect any objects")

    # Return the results
    return {
        "positions_scanned": len(scan_results),
        "objects_detected": all_objects,
        "unique_objects": unique_objects,
        "selected_object": selected_object if object_count > 0 and selected_object else None
    }


@inlineCallbacks
def main(session, details):
    """Main entry point when the WAMP session is established."""
    logger.info("WAMP session established")

    # Get the scan mode from command line arguments
    scan_mode = MODE_360 if args.mode == '360' else MODE_STATIC

    # Get difficulty level
    difficulty = args.difficulty

    # Wait for a moment to ensure everything is initialized
    yield sleep(2)

    # Test a single image capture first
    yield test_single_image(session)

    # Run the full scan test with pointing enabled/disabled based on command line argument
    # and include the difficulty parameter for object selection
    scan_results = yield run_scan_test(
        session,
        scan_mode=scan_mode,
        point_enabled=not args.no_point,
        difficulty=difficulty
    )

    # Report final results
    positions_scanned = scan_results["positions_scanned"]
    objects_count = len(scan_results["unique_objects"])
    logger.info(f"Test complete. Scanned {positions_scanned} positions, detected {objects_count} unique objects")

    # Report selected object for the I Spy game
    if "selected_object" in scan_results and scan_results["selected_object"]:
        selected_obj = scan_results["selected_object"]
        logger.info(f"Selected object for I Spy game: {selected_obj['name']} ({selected_obj.get('dutch_name', '')})")

    # Keep the session alive for a moment
    logger.info("Tests completed. Keeping session alive for 10 seconds...")
    yield sleep(10)

    logger.info("Test script finished")


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test scanner for robot vision")
    parser.add_argument('--no-point', action='store_true', default=False,
                        help='Disable pointing to detected objects')
    parser.add_argument('--mode', choices=['static', '360'], default='360',
                        help='Scan mode: static (head movement only) or 360 (full rotation)')
    parser.add_argument('--difficulty', type=int, choices=[1, 2, 3], default=1,
                        help='Difficulty level for the I Spy game (1=easy, 2=medium, 3=hard)')
    args = parser.parse_args()

    # Configure WAMP component
    wamp = Component(
        transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0
        }],
        realm="rie.67d2ae3c99b259cf43b05300",
    )

    # Register the main function
    wamp.on_join(main)

    # Run the component
    run([wamp])