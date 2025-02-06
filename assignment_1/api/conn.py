import os

from dotenv import load_dotenv


# Determine the absolute path to the .env file
def find_dotenv():
    current_dir = os.getcwd()
    print(current_dir)

    while current_dir != os.path.abspath(os.sep):
        potential_env_path = os.path.join(current_dir, '.env')
        if os.path.isfile(potential_env_path):
            return potential_env_path
        current_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    raise FileNotFoundError("Could not find the .env file")

dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

def chat_gtp_connection():
    return os.getenv('CHATGTP_API')