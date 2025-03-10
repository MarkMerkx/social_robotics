# test_scanner.py
"""
Standalone test script to verify the object scanning and recognition functionality
without running the full I Spy game.

This can be run directly to test the scanner component in isolation.
"""

import os
import sys
import random
import argparse
import logging
from autobahn.twisted.component import Component, run
from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep

# Make sure the assignment_3 package is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Import the scanner module
from assignment_3.vision.scanning import ObjectScanner
from assignment_3.vision.debug_ui import DebugServer, save_debug_data
from assignment_3.gesture_control.scanning_gestures import (
    perform_scan_gesture,
    perform_scan_360,
    perform_point_to
)

# Set up logging
logging.basicConfig(
    format='%(asctime)s SCANNER TEST %(levelname)-8s %(message)s',
    level=logging.DEBUG,
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Create debug UI server
debug_server = DebugServer(port=8080)


@inlineCallbacks
def test_scanning(session):
    """
    Run a test scan and display the results.
    """
    logger.info("Starting scanner test")

    # Initialize the scanner
    scanner = ObjectScanner(session)

    # Make the robot aware we're in test mode
    yield session.call("rie.dialogue.say", text="Starting scanner test mode")
    yield sleep(2)

    # Start the debug server
    debug_server.start()

    # Perform the scan
    try:
        logger.info("Beginning environmental scan")
        yield session.call("rie.dialogue.say", text="Starting to scan the environment")
        yield sleep(1)

        # Test the scanning gesture first
        yield perform_scan_gesture(session)
        yield sleep(1)

        # Then perform the full scan
        detected_objects = yield scanner.perform_full_scan()

        yield session.call("rie.dialogue.say", text=f"Scan complete. Found {len(detected_objects)} objects.")
        logger.info(f"Scan complete. Found {len(detected_objects)} unique objects")

        # Update debug UI with results
        debug_server.update_data(detected_objects, scanner.image_buffer)

        # Also save to disk for later inspection
        save_debug_data(detected_objects, scanner.image_buffer)

        # If objects were found, demonstrate pointing to a random object
        if detected_objects:
            random_object = random.choice(list(detected_objects.keys()))
            logger.info(f"Demonstrating pointing to: {random_object}")

            yield session.call("rie.dialogue.say", text=f"I will now point to the {random_object}")
            yield sleep(1)

            yield scanner.point_to_object(random_object)
            yield sleep(3)

            # Reset head position
            yield scanner._reset_head_position()

    except Exception as e:
        logger.error(f"Error during scanner test: {e}")
        yield session.call("rie.dialogue.say", text="An error occurred during the scan test")

    # Keep the server running for manual inspection
    logger.info("Test complete. Debug UI server running at http://localhost:8080")
    logger.info("Press Ctrl+C to exit")

    # Keep session alive
    while True:
        yield sleep(1)


@inlineCallbacks
def test_individual_gestures(session):
    """
    Test individual scanning gestures.
    """
    logger.info("Testing individual scanning gestures")

    # Make the robot aware we're in test mode
    yield session.call("rie.dialogue.say", text="Testing scanning gestures")
    yield sleep(1)

    # Test scan gesture
    yield session.call("rie.dialogue.say", text="Testing scan gesture")
    yield perform_scan_gesture(session)
    yield sleep(2)

    # Test 360 scan
    yield session.call("rie.dialogue.say", text="Testing 360 scan")
    yield perform_scan_360(session)
    yield sleep(2)

    # Test pointing gestures
    yield session.call("rie.dialogue.say", text="Testing pointing to the left")
    yield perform_point_to(session, 30)  # Point 30 degrees to the left
    yield sleep(2)

    yield session.call("rie.dialogue.say", text="Testing pointing to the right")
    yield perform_point_to(session, -30)  # Point 30 degrees to the right
    yield sleep(2)

    # Reset position
    yield session.call("rom.motion.joint.move", joint="body.head.yaw", angle=0.0, speed=0.5)
    yield session.call("rom.motion.joint.move", joint="body.head.pitch", angle=0.0, speed=0.5)
    yield session.call("rom.motion.joint.move", joint="body.arms.left.upper.pitch", angle=0.0, speed=0.5)
    yield session.call("rom.motion.joint.move", joint="body.arms.right.upper.pitch", angle=0.0, speed=0.5)

    yield session.call("rie.dialogue.say", text="Gesture tests complete")
    logger.info("Gesture tests complete")


@inlineCallbacks
def main(session, details):
    """
    Main function called when the WAMP session is joined.
    """
    logger.info("WAMP session joined")

    # Optional behavior: play an initial animation
    yield session.call("rom.optional.behavior.play", name="BlocklyCrouch")
    yield session.call("rie.dialogue.say", text="Initializing scanner test...")
    yield sleep(2)

    # Parse command line arguments to determine test mode
    if args.gestures_only:
        # Test just the gestures
        yield test_individual_gestures(session)
    else:
        # Run the full scanner test
        yield test_scanning(session)

    # Keep the session alive
    while True:
        yield sleep(1)


if __name__ == "__main__":
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Test the object scanner component")
    parser.add_argument("--realm", default="rie.67b7052ba06ea6579d140a02",
                        help="WAMP realm to connect to")
    parser.add_argument("--url", default="ws://wamp.robotsindeklas.nl",
                        help="WebSocket URL to connect to")
    parser.add_argument("--gestures-only", action="store_true",
                        help="Test only the scanning gestures without object detection")

    args = parser.parse_args()

    # Configure WAMP component
    wamp = Component(
        transports=[{
            "url": args.url,
            "serializers": ["msgpack"],
            "max_retries": 0
        }],
        realm=args.realm,
    )

    # Register the main function to be called when the session is established
    wamp.on_join(main)

    # Run the component
    logger.info(f"Connecting to {args.url}, realm {args.realm}")
    run([wamp])