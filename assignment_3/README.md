# I Spy Game with Alpha Mini Robot

This is an interactive "I Spy" game where you can play with the Alpha Mini robot. The robot can guess an object you choose or have you guess an object it picks, using speech and scanning features.

## Prerequisites
- **Python 3.8 or higher**: Make sure Python is installed. (we've used 3.11)
- **Required Libraries**: You’ll need `twisted` and `autobahn` for WAMP communication. In addition check requirements.txt
- **Alpha Mini Robot**: Must be powered on and connected to the WAMP server.


## Setup Instructions

### Install Dependencies
Run this command to install the necessary Python libraries:
```bash
pip install -r requirements.txt
```

### Set Up the Environment File
1. Create a `.env` file in the `assignment_3` directory.
2. Add valid openAI api key
```env
OPENAI_API_KEY = sk.....
```


### In main.py
Adjust this line to set the WAMP realm for the robot:
```main
realm="rie.67e1353e540602623a34dfec",
```

## How to Run the Game
Start the game by running the main script:
```bash
python main.py
```

### Command-Line Arguments
You can customize the robot’s scanning behavior with the `--scan-mode` argument:
- `--scan-mode static`: Uses a fixed field of view (default).
- `--scan-mode 360`: Makes the robot rotate for a 360-degree scan.

**Example:**
```bash
python main.py --scan-mode 360
```

## General Game Flow
### Start Up
- The robot crouches and says, "Initializing the game..."

### Hello
- It asks for your name and greets you.

### Play or Not
- The robot asks if you want to play. Say "yes" to continue.

### Choose a Mode
- Decide if **you guess the object** ("I guess") or **the robot guesses** ("You guess").

### Gameplay
- Speak to answer the robot’s questions or give hints.
- The robot listens and responds with guesses or clues, depending on the mode.

### Play Again
- After finishing, the robot asks if you’d like another round.

