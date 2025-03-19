def dialogue_with_reprompt(prompt, gesture, n, session, stt, timeout=20):
    yield say_animated(session, prompt, gesture_name="beat_gesture")
    yield sleep(5)

    # Wait for the user's answer.
    reponse = yield wait_for_response(None, session, stt, timeout=timeout)
    if not reponse:
        reponse = "No response"
        logger.debug("No feedback received; defaulting to: %s", feedback)
        return dialogue_with_reprompt(prompt, gesture, n =+1 , session, stt, timeout)  # call recursively
    return

