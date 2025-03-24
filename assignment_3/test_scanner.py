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
import json
from gesture_control.point_to_object import point_to_object
# Import modules
from vision.image_capture import initialize_image_directory, capture_image
from vision.object_recognition import initialize_object_directory, detect_objects, get_unique_objects, save_detection_results
from gesture_control.scanning import (
    perform_scan,
    MODE_STATIC,
    MODE_360
)
from utils.helpers import setup_logging, format_object_list, process_detected_objects

# Import hint generation functions
from assignment_3.api.api_handler import (
    choose_object,
    give_hint,
    start_i_spy_game,
    process_guess
)

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

        # Disable YOLO if requested
        use_yolo = kwargs.get('use_yolo', False)  # Default to False for I Spy game

        # Detect objects in the image with position info
        objects, annotated_path = detect_objects(
            image,
            position_info=position_info,
            use_chatgpt=use_chatgpt,
            use_yolo=use_yolo
        )

        return objects

    except Exception as e:
        logger.error(f"Error in capture_and_analyze: {e}")
        return {}


@inlineCallbacks
def demo_hints(session, game_object, difficulty, num_rounds=3):
    """
    Demonstrate hint generation for the I Spy game.

    :param session: The WAMP session
    :type session: Component
    :param game_object: The selected game object
    :type game_object: dict
    :param difficulty: Difficulty level (1-3)
    :type difficulty: int
    :param num_rounds: Number of additional hints to demonstrate
    :type num_rounds: int
    :return: List of all hints generated
    :rtype: list
    """
    try:
        # Start the game with an initial introduction and hint
        intro, initial_hint = start_i_spy_game(game_object, difficulty)

        logger.info(f"I Spy game introduction: {intro}")
        logger.info(f"Initial hint: {initial_hint}")

        # Have the robot say the introduction and initial hint
        yield session.call("rie.dialogue.say", text=intro)
        yield sleep(0.5)  # Brief pause between sentences
        yield session.call("rie.dialogue.say", text=initial_hint)

        # Track all hints provided
        all_hints = [initial_hint]

        # Generate and demonstrate additional hints
        for round_num in range(num_rounds):
            # Add a delay to simulate game progression
            yield sleep(1.0)

            # Generate the next hint
            next_hint = give_hint(
                game_object,
                difficulty=difficulty,
                round_num=round_num+1,  # First additional hint is round 1
                previous_hints=all_hints,
                is_initial_hint=False
            )

            logger.info(f"Round {round_num+1} hint: {next_hint}")
            yield session.call("rie.dialogue.say", text=next_hint)

            # Add to our collection of hints
            all_hints.append(next_hint)

        return all_hints

    except Exception as e:
        logger.error(f"Error in demo_hints: {e}")
        return []


@inlineCallbacks
def run_scan_test(session, scan_mode=MODE_STATIC, point_enabled=True, difficulty=1, use_yolo=False):
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
    :param use_yolo: Whether to use YOLO for object detection
    :type use_yolo: bool
    :return: Dictionary with scan results and selected object
    :rtype: dict
    """
    mode_name = "360-degree" if scan_mode == MODE_360 else "static"
    logger.info(f"Starting {mode_name} scan test")

    # Log detection method configuration
    detection_methods = []
    if use_yolo:
        detection_methods.append("YOLO")
    detection_methods.append("ChatGPT Vision")
    logger.info(f"Using detection methods: {', '.join(detection_methods)}")

    # Announce start of scan
    yield session.call("rie.dialogue.say", text=f"Starting {mode_name} environment scan")

    # Create extra parameters to pass to capture_and_analyze
    extra_params = {
        "use_yolo": use_yolo
    }

    # Perform the scan using the capture_and_analyze function with extra parameters
    scan_results, all_objects = yield perform_scan(
        session,
        mode=scan_mode,
        capture_callback=capture_and_analyze,
        process_callback=process_detected_objects,
        extra_context=extra_params
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
        selected_object = choose_object(all_objects, difficulty)

        if selected_object:
            logger.info(
                f"Selected object for I Spy game: {selected_object['name']} ({selected_object.get('dutch_name', 'unknown')})")
            logger.info(f"Object features: {selected_object.get('features', {})}")
            logger.info(f"Object position: {selected_object.get('position_id', 'unknown')}")

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
                "cumulative_rotation": selected_object.get('cumulative_rotation', 0),
                "difficulty": difficulty  # Add difficulty to the game object
            }

            # Save the game object to a file for later use
            try:
                with open('current_game_object.json', 'w') as f:
                    json.dump(game_object, f, indent=2)
                logger.info("Saved game object to current_game_object.json")
            except Exception as e:
                logger.error(f"Error saving game object: {e}")

            # Demo the hint system by generating an initial hint and some additional hints
            logger.info(f"Demonstrating I Spy hints for difficulty level {difficulty}...")

            # Generate and demonstrate hints (initial + 2 additional hints)
            all_hints = yield demo_hints(session, game_object, difficulty, num_rounds=2)

            # Save the hints to the game object file for reference
            game_object['hints'] = all_hints
            try:
                with open('current_game_object.json', 'w') as f:
                    json.dump(game_object, f, indent=2)
                logger.info(f"Updated game object with {len(all_hints)} hints")
            except Exception as e:
                logger.error(f"Error updating game object with hints: {e}")

            # Add demonstration of pointing to the object if enabled
            if point_enabled:
                yield sleep(1.0)  # Pause before pointing
                yield session.call("rie.dialogue.say", text=f"Let me show you what I was thinking of.")

                # Calculate pointing angle based on stored position
                yaw = game_object.get('yaw', 0)
                cumulative_rotation = game_object.get('cumulative_rotation', 0)
                pointing_angle = yaw

                # If we're in 360 mode, adjust for the robot's rotation
                if scan_mode == MODE_360:
                    pointing_angle = pointing_angle + cumulative_rotation

                # Point to the object
                logger.info(f"Pointing to {game_object['name']} at angle {pointing_angle}")
                yield point_to_object(session, selected_object)

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

    # Get parameters from command line arguments
    scan_mode = MODE_360 if args.mode == '360' else MODE_STATIC
    difficulty = args.difficulty
    use_yolo = args.use_yolo

    # Wait for a moment to ensure everything is initialized
    yield sleep(2)

    # Run the full scan test with specified parameters
    scan_results = yield run_scan_test(
        session,
        scan_mode=scan_mode,
        point_enabled=not args.no_point,
        difficulty=difficulty,
        use_yolo=use_yolo
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
    parser.add_argument('--use-yolo', action='store_true', default=False,
                        help='Enable YOLO object detection (disabled by default for I Spy game)')
    parser.add_argument('--hints-only', action='store_true', default=False,
                        help='Skip scanning and only demonstrate hints with the last saved object')
    args = parser.parse_args()

    # Configure WAMP component
    wamp = Component(
        transports=[{
            "url": "ws://wamp.robotsindeklas.nl",
            "serializers": ["msgpack"],
            "max_retries": 0
        }],
        realm="rie.67e12f7d540602623a34dfbb",
    )

    # Register the main function
    wamp.on_join(main)

    # Run the component
    run([wamp])