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
from vision.object_recognition import initialize_object_directory, detect_objects, get_unique_objects
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

        # Create position info
        position_info = {
            'yaw': yaw,
            'pitch': pitch,
            'turn': kwargs.get('turn', 0),
            'cumulative_rotation': kwargs.get('cumulative_rotation', 0)
        }

        # Detect objects in the image
        objects, _ = detect_objects(image, position_info)

        return objects

    except Exception as e:
        logger.error(f"Error in capture_and_analyze: {e}")
        return {}


@inlineCallbacks
def test_single_image(session):
    """Test capturing and analyzing a single image."""
    logger.info("Testing single image capture and analysis")

    # Capture image
    result = yield capture_image(session)
    if result:
        image, filename = result
        logger.info(f"Captured test image: {filename}")

        # Detect objects
        objects, annotated_path = detect_objects(image)

        if objects:
            logger.info(f"Detected {len(objects)} objects in test image")
            for obj_id, obj_data in objects.items():
                logger.info(f"  {obj_data['name']} (confidence: {obj_data['confidence']:.2f})")
        else:
            logger.info("No objects detected in test image")

        return True
    else:
        logger.warning("Failed to capture test image")
        return False


@inlineCallbacks
def run_scan_test(session, scan_mode=MODE_STATIC, point_enabled=True):
    """
    Run a complete scan test with the specified mode.

    :param session: The WAMP session
    :type session: Component
    :param scan_mode: Scan mode ("static" or "360")
    :type scan_mode: str
    :param point_enabled: Whether to point to detected objects
    :type point_enabled: bool
    :return: Dictionary with scan results
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

        # If objects were found and pointing is enabled, point to the first one as a demo
        if len(all_objects) > 0 and point_enabled:
            # Get first object's position
            first_obj = next(iter(all_objects.values()))
            if 'position' in first_obj:
                pos = first_obj['position']
                obj_name = first_obj['name']

                # Calculate pointing angle, accounting for cumulative rotation if in 360 mode
                pointing_angle = pos['yaw']
                if 'cumulative_rotation' in pos and scan_mode == MODE_360:
                    # Adjust for the robot's rotation
                    pointing_angle = pointing_angle + pos['cumulative_rotation']

                # Point to the object
                logger.info(f"Pointing to {obj_name} at angle {pointing_angle}")
                yield session.call("rie.dialogue.say", text=f"I'll point to the {obj_name}")
                yield point_to_object(session, pointing_angle, pos['pitch'])
        elif not point_enabled:
            logger.info("Pointing is disabled, skipping point gesture")
    else:
        logger.info("Scan complete. No objects detected.")
        yield session.call("rie.dialogue.say", text="Scan complete. I didn't detect any objects")

    # Return the results
    return {
        "positions_scanned": len(scan_results),
        "objects_detected": all_objects,
        "unique_objects": unique_objects
    }


@inlineCallbacks
def main(session, details):
    """Main entry point when the WAMP session is established."""
    logger.info("WAMP session established")

    # Get the scan mode from command line arguments
    scan_mode = MODE_360 if args.mode == '360' else MODE_STATIC

    # Wait for a moment to ensure everything is initialized
    yield sleep(2)

    # Test a single image capture first
    yield test_single_image(session)

    # Run the full scan test with pointing enabled/disabled based on command line argument
    scan_results = yield run_scan_test(
        session,
        scan_mode=scan_mode,
        point_enabled=not args.no_point
    )

    # Report final results
    positions_scanned = scan_results["positions_scanned"]
    objects_count = len(scan_results["unique_objects"])
    logger.info(f"Test complete. Scanned {positions_scanned} positions, detected {objects_count} unique objects")

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
    args = parser.parse_args()

    # Configure WAMP component
    wamp = Component(
        transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0
        }],
        realm="rie.67cff07599b259cf43b04548",
    )

    # Register the main function
    wamp.on_join(main)

    # Run the component
    run([wamp])