"""
Helper utilities for robot applications, with colorized logging per module.
"""
import os
import sys
import logging
import time
from colorama import Fore, Style, init

# Initialize colorama so colors render correctly on all platforms
init(autoreset=True)

# Dictionary of module substrings => color
MODULE_COLORS = {
    "object_recognition": Fore.MAGENTA,
    "api_handler": Fore.BLUE,
    "game_handler": Fore.YELLOW,
    "scanning": Fore.CYAN,
    "gesture_control": Fore.GREEN,
    "vision": Fore.LIGHTBLUE_EX,
    "DEFAULT": Fore.WHITE
}

# Dictionary of levelname => color
LEVEL_COLORS = {
    "DEBUG": Style.DIM + Fore.WHITE,
    "INFO": Fore.GREEN,
    "WARNING": Fore.YELLOW,
    "ERROR": Fore.RED,
    "CRITICAL": Fore.RED + Style.BRIGHT
}


class ModuleColorFormatter(logging.Formatter):
    """
    Custom formatter that assigns colors based on the module name (logger.name)
    and the log level, then prints the time, module label, log level, and message.
    """

    def format(self, record):
        # Convert record's creation time to an HH:MM:SS string
        time_str = time.strftime("%H:%M:%S", time.localtime(record.created)) + f".{int(record.msecs):03d}"


        # Determine level color
        level_color = LEVEL_COLORS.get(record.levelname, Fore.WHITE)

        # Determine module color by checking record.name
        # If none of the known modules is found in record.name, fallback to DEFAULT
        module_color = MODULE_COLORS["DEFAULT"]
        for mod_substring, color in MODULE_COLORS.items():
            if mod_substring != "DEFAULT" and mod_substring.lower() in record.name.lower():
                module_color = color
                break

        # Use the parent formatter (which is just '%(message)s') to get the message
        message = super().format(record)

        # Construct the final colored line:
        # e.g. "12:34:56 [object_recognition] INFO: My log message"
        return (
            f"{time_str} "
            f"{module_color}[{record.name}]{Style.RESET_ALL} "
            f"{level_color}{record.levelname}{Style.RESET_ALL}: "
            f"{message}"
        )


def setup_logging():
    """
    Set up a global, colorized logger for the entire application.
    """
    # Create a root logger at INFO level (adjust if you want more/less detail)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Remove any old handlers so we don't duplicate logs
    root_logger.handlers.clear()

    # Create a StreamHandler for console output
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)

    # Use a custom log format that only includes the raw message; we build the rest in ModuleColorFormatter
    console_format = "%(message)s"
    console_formatter = ModuleColorFormatter(console_format)
    console_handler.setFormatter(console_formatter)

    # Attach console handler
    root_logger.addHandler(console_handler)

    # Optionally, you can still configure a file handler if you want log files
    # (Uncomment and adjust the path below to enable)
    """
    log_file_path = "robot.log"
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s %(name)s %(levelname)s: %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    """

    # Example: silence certain libraries’ debug logs
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


def create_directory(directory):
    """
    Create a directory if it doesn't exist.
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
    """
    if not objects_dict:
        return "no objects"

    sorted_objects = sorted(objects_dict.items(), key=lambda x: x[1], reverse=True)
    object_names = [name for name, count in sorted_objects]

    if len(object_names) == 1:
        return object_names[0]
    elif len(object_names) == 2:
        return f"{object_names[0]} and {object_names[1]}"
    else:
        return ", ".join(object_names[:-1]) + f", and {object_names[-1]}"


def process_detected_objects(existing_objects, new_objects):
    """
    Update a master list of objects with best confidence.
    """
    if not new_objects:
        return existing_objects

    result = existing_objects.copy()

    for obj_id, obj_data in new_objects.items():
        obj_name = obj_data['name']
        existing_id = None

        for key in result:
            if (
                isinstance(result[key], dict)
                and 'name' in result[key]
                and result[key]['name'] == obj_name
            ):
                existing_id = key
                break

        # Only replace if new object has higher confidence
        if existing_id and result[existing_id]['confidence'] >= obj_data['confidence']:
            continue

        result[obj_id] = obj_data

    return result
