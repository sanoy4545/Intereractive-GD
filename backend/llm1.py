from flask import Blueprint, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
import io
from gtts import gTTS
import os
import requests
import logging
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize a Blueprint for LLM routes
llm_bp = Blueprint('llm1', __name__)
CORS(llm_bp, resources={r"/*": {"origins": "*"}})  # Enable CORS for frontend communication

def init_api_keys():
    try:
        load_dotenv()
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is required")
        
        # Initialize OpenAI client with OpenRouter
        global client
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        logger.info("Successfully configured OpenRouter API")
    except Exception as e:
        logger.error(f"Error in initializing API keys: {e}")
        raise

# Initialize API keys when the blueprint is created
init_api_keys()

@llm_bp.route('/api/llm1/llm', methods=['POST'])
def get_llm_response():
    try:
        data = request.get_json()
        if not data or not data.get("text"):
            return jsonify({"success": False, "error": "No text provided"}), 400

        text = data.get("text")
        topic = data.get("topic", "")
        is_initial = data.get("is_initial_message", False)
        is_user_message = data.get("is_user_message", False)

        if is_initial:
            prompt = f"""You are starting a group discussion about "{topic}". Give a simple introduction in 40-50 words that sets the context and invites others to share their views. Use plain text without any special characters or emojis. Speak in a male voice."""
        elif is_user_message:
            prompt = f"""You are in a group discussion about "{topic}". A participant just said: "{text}". Respond directly to their point in 40-50 words. Use plain text without any special characters or emojis. Keep your response simple and conversational. Speak in a male voice."""
        else:
            prompt = f"""You are in a group discussion about "{topic}". Respond in 40-50 words to: {text}. Use plain text without any special characters or emojis. Keep your response simple and conversational. Speak in a male voice."""

        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:8080",  # Your site URL
                "X-Title": "Interactive GD",  # Your site name
            },
            model="google/gemini-pro",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        response_text = completion.choices[0].message.content.strip()
        if len(response_text.split()) > 55:
            response_text = ' '.join(response_text.split()[:50]) + '...'

        return jsonify({
            "success": True,
            "response": response_text,
            "model_used": "google/gemini-pro"
        })

    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@llm_bp.route('/api/llm1/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.get_json()
        if not data or not data.get("text"):
            return jsonify({"success": False, "error": "No text provided"}), 400

        text = data.get("text")
        # Using 'co.uk' tld for a more British male voice and explicitly setting male voice parameters
        tts = gTTS(text=text, lang='en', tld='co.uk', slow=False)
        
        audio_stream = io.BytesIO()
        tts.write_to_fp(audio_stream)
        audio_stream.seek(0)
        
        return send_file(audio_stream, mimetype="audio/mp3")
    
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

# This is an alternative implementation if you want to try another option
@llm_bp.route('/api/tts/alt', methods=['POST'])
def alt_text_to_speech():
    """Alternative TTS using pyttsx3 with a male voice."""
    try:
        import pyttsx3
        import tempfile
        import os
        
        data = request.get_json()
        text = data.get("text")

        if not text:
            return jsonify({"success": False, "error": "No text provided"}), 400

        # Initialize the pyttsx3 engine
        engine = pyttsx3.init()
        
        # Get available voices
        voices = engine.getProperty('voices')
        
        # Select a male voice (usually the first voice is male)
        engine.setProperty('voice', voices[1].id)
        
        # Set appropriate rate and volume for male voice
        engine.setProperty('rate', 150)  # Speed
        engine.setProperty('volume', 0.9)  # Volume
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
        temp_filename = temp_file.name
        temp_file.close()
        
        # Save to the temporary file
        engine.save_to_file(text, temp_filename)
        engine.runAndWait()
        
        # Return the file
        return send_file(temp_filename, mimetype="audio/mp3")
        
    except Exception as e:
        print(f"Error in pyttsx3 conversion: {e}")
        return jsonify({"success": False, "error": f"Alternative TTS failed: {str(e)}"}), 500