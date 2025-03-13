"""
ChatGPT Vision API client for enhanced object recognition.

Provides functionality to classify objects in images using the ChatGPT Vision API.
"""

import os
import base64
import logging
import json
import sys
import time
from PIL import Image
import io
from ..api.conn import chat_gtp_connection

# Configure logging
logger = logging.getLogger(__name__)

def encode_image_to_base64(image):
    """
    Encode a PIL Image to base64 string.

    :param image: PIL Image to encode
    :type image: PIL.Image
    :return: Base64 encoded string
    :rtype: str
    """
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_image_with_chatgpt_vision(image, prompt=None):
    """
    Analyze an image using ChatGPT Vision API.

    :param image: Image to analyze
    :type image: PIL.Image
    :param prompt: Custom prompt to send to the API
    :type prompt: str or None
    :return: Analysis results
    :rtype: dict
    """
    try:
        # Try to import OpenAI client
        from openai import OpenAI
        client = OpenAI()
    except ImportError:
        logger.error("OpenAI Python client not installed. Please install it with: pip install openai")
        return {"error": "OpenAI client not installed"}

    api_key = chat_gtp_connection()

    if not api_key:
        logger.warning("OpenAI API key not found in environment variables")
        return {"error": "API key not configured"}

    # Resize image if it's too large (to reduce API costs)
    max_dim = 800
    if image.width > max_dim or image.height > max_dim:
        ratio = min(max_dim / image.width, max_dim / image.height)
        new_width = int(image.width * ratio)
        new_height = int(image.height * ratio)
        image = image.resize((new_width, new_height), Image.LANCZOS)
        logger.info(f"Resized image to {new_width}x{new_height} for API request")

    # Encode the image to base64
    base64_image = encode_image_to_base64(image)

    # Default prompt if none provided
    if prompt is None:
        prompt = """
        Analyze this image and identify all objects visible. For each object, provide:
        1. The object name
        2. A confidence score from 0 to 1
        3. A brief description

        Format your response as a JSON with this structure:
        {
            "objects": [
                {
                    "name": "object_name",
                    "confidence": 0.95,
                    "description": "brief description"
                },
                ...
            ]
        }
        Only respond with valid JSON.
        """

    try:
        logger.info("Sending request to ChatGPT Vision API")

        completion = client.chat.completions.create(
            model="gpt-4o-mini",  # Using GPT-4o with vision capabilities
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{base64_image}",
                            },
                        },
                    ],
                }
            ],
            max_tokens=300
        )

        # Extract response
        result_text = completion.choices[0].message.content

        # Try to extract JSON from the response if it contains it
        try:
            # Find JSON part in the response
            json_start = result_text.find('{')
            json_end = result_text.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = result_text[json_start:json_end]
                result = json.loads(json_str)
                logger.info(f"Successfully parsed JSON response from ChatGPT Vision API")
                return result
            else:
                # If no JSON found, return the raw text
                logger.warning("No JSON found in ChatGPT Vision API response")
                return {"raw_response": result_text}
        except json.JSONDecodeError:
            logger.warning("Failed to parse JSON from ChatGPT Vision API response")
            return {"raw_response": result_text}

    except Exception as e:
        logger.error(f"Error in OpenAI API call: {str(e)}")
        return {"error": str(e)}

def get_chatgpt_vision_objects(image):
    """
    Get object detections using ChatGPT Vision API.

    :param image: Image to analyze
    :type image: PIL.Image
    :return: Dictionary of detected objects
    :rtype: dict
    """
    timestamp = int(time.time())

    # Call the API
    analysis_result = analyze_image_with_chatgpt_vision(image)

    # Process the result into the expected format
    detected_objects = {}

    if "objects" in analysis_result:
        for i, obj in enumerate(analysis_result["objects"]):
            object_id = f"gpt_{obj['name']}_{i}"

            # Create object entry
            detected_objects[object_id] = {
                'name': obj['name'],
                'confidence': obj.get('confidence', 0.9),  # Default confidence if not provided
                'source': 'chatgpt',
                'description': obj.get('description', ''),
            }
    elif "raw_response" in analysis_result:
        # Store raw response as a single object if JSON parsing failed
        object_id = f"gpt_analysis_{timestamp}"
        detected_objects[object_id] = {
            'name': 'gpt_analysis',
            'confidence': 1.0,
            'source': 'chatgpt',
            'raw_text': analysis_result["raw_response"],
        }
    elif "error" in analysis_result:
        # Log the error but return empty results to not break the flow
        logger.error(f"ChatGPT Vision API error: {analysis_result['error']}")
        return {}

    logger.info(f"ChatGPT Vision API detected {len(detected_objects)} objects")
    return detected_objects