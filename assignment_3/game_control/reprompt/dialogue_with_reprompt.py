def dialogue_with_reprompt(prompt, gesture, n, session, stt, timeout=20):
    yield say_animated(session, prompt, gesture_name="beat_gesture")
    yield sleep(5)

    # Wait for the user's answer.
    reponse = yield wait_for_response(None, session, stt, timeout=20)
    if not reponse:
        reponse = "No response"
        logger.debug("No feedback received; defaulting to: %s", feedback)
    else:
        logger.debug("Feedback received: %s", feedback)
        return

    n += 1
    return dialogue_with_reprompt() # call recursively