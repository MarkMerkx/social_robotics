from twisted.internet.defer import inlineCallbacks
from autobahn.twisted.util import sleep
from assignment_3.gesture_control.say_animated import say_animated
from assignment_3.api.give_hint import give_hint
import logging
import re

logger = logging.getLogger(__name__)

class DialogueManager:
    def __init__(self, session, stt):
        self.session = session  # WAMP session for TTS and gestures
        self.stt = stt  # SpeechToText instance
        self.language = "en-US"  # Default to English for STT
        self.default_timeout = 15  # Default timeout in seconds

    @inlineCallbacks
    def say(self, text, gesture=None):
        """
        Speak text with an optional gesture, switching to Dutch TTS for <nl>...</nl> tagged words.

        Args:
            text (str): The text to speak, with Dutch words marked as <nl>word</nl>.
            gesture (str, optional): Gesture to perform while speaking the first segment.
        """
        pattern = re.compile(r'(<nl>.*?</nl>)')
        segments = pattern.split(text)
        first_segment = True
        for segment in segments:
            if segment.startswith('<nl>') and segment.endswith('</nl>'):
                dutch_word = segment[4:-5]
                yield say_animated(self.session, dutch_word, gesture_name=None, lang="nl")
                logger.debug(f"Spoke Dutch: '{dutch_word}' in nl")
            elif segment.strip():
                if first_segment:
                    yield say_animated(self.session, segment, gesture_name=gesture, lang="en")
                    first_segment = False
                else:
                    yield say_animated(self.session, segment, gesture_name=None, lang="en")
                logger.debug(f"Spoke English: '{segment}' in en")

    @inlineCallbacks
    def listen(self, timeout=None, silence_after_speech=2.0, poll_interval=1.0):
        """
        Listen for a response with incremental checking, a total timeout, and silence detection.

        :param timeout: Maximum time to wait for a response (seconds), defaults to self.default_timeout
        :param silence_after_speech: Time to wait after detecting speech to confirm end (seconds)
        :param poll_interval: How often to check for STT words (seconds)
        :return: The detected response or None if timeout is reached
        """
        timeout = timeout or self.default_timeout
        self.stt.words = []
        waited = 0.0
        response = None
        silence_waited = 0.0

        logger.debug(f"Starting listen with timeout={timeout}s, silence_after_speech={silence_after_speech}s")

        while waited < timeout:
            yield sleep(poll_interval)
            waited += poll_interval
            words = self.stt.give_me_words()

            if words:
                if isinstance(words[0], str):
                    response = " ".join(words)
                elif isinstance(words[0], tuple) and len(words[0]) > 0 and isinstance(words[0][0], str):
                    response = " ".join([word[0] for word in words])
                else:
                    logger.warning(f"Unexpected type in words: {type(words[0])}")
                    response = None

                logger.debug(f"Detected speech after {waited:.1f}s: {response}")

                while silence_waited < silence_after_speech:
                    yield sleep(poll_interval)
                    silence_waited += poll_interval
                    waited += poll_interval
                    new_words = self.stt.give_me_words()

                    if new_words != words:
                        words = new_words
                        silence_waited = 0.0
                        if isinstance(words[0], str):
                            response = " ".join(words)
                        elif isinstance(words[0], tuple) and len(words[0]) > 0 and isinstance(words[0][0], str):
                            response = " ".join([word[0] for word in words])
                        logger.debug(f"More speech detected, updated response: {response}")

                    if waited >= timeout:
                        logger.debug(f"Timeout reached during silence wait, returning: {response}")
                        return response

                logger.debug(f"Silence detected for {silence_after_speech}s, returning: {response}")
                return response
            else:
                logger.debug(f"Waiting for speech... ({waited:.1f}/{timeout}s)")

        logger.debug(f"Timeout ({timeout}s) reached with no response.")
        return None

    @inlineCallbacks
    def ask_with_reprompt(self, prompt, gesture=None, max_attempts=3, game_context=None, timeout=None):
        """
        Ask a question and reprompt with varied phrasing if needed.

        :param prompt: Initial question
        :param gesture: Optional gesture
        :param max_attempts: Number of reprompts
        :param game_context: Dict with game info (game_object, difficulty, etc.)
        :param timeout: Time to wait for response
        :return: User's response or None
        """
        reprompt_phrases = [
            "Any guesses yet? What do you think it is?",
            "Still curious! What’s your guess?",
            "No answer yet? Try a guess or say 'hint'!"
        ]

        for attempt in range(max_attempts):
            current_prompt = prompt if attempt == 0 else reprompt_phrases[min(attempt - 1, len(reprompt_phrases) - 1)]
            yield self.say(current_prompt, gesture)
            response = yield self.listen(timeout=timeout)

            if response:
                response_lower = response.lower()
                if "repeat" in response_lower:
                    continue
                elif "hint" in response_lower and game_context:
                    hint = give_hint(game_context['game_object'], game_context['difficulty'], game_context['round_num'])
                    yield self.say(hint, gesture="beat_gesture")
                    # Check understanding for Dutch hints (handled below)
                    response = yield self.listen(timeout=timeout)
                    if response:
                        return response
                else:
                    return response
            elif attempt == 1 and game_context:  # After second timeout, offer a hint
                yield self.say("Seems tricky! Here’s a hint to help.", gesture="beat_gesture")
                hint = give_hint(game_context['game_object'], game_context['difficulty'], game_context['round_num'])
                yield self.say(hint, gesture="beat_gesture")
                # Check understanding for Dutch hints (handled below)
            elif attempt == max_attempts - 1:
                yield self.say("Let’s move on—no guess this time!", gesture="shake_no")
                return None