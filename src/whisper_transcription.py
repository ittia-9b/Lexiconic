import os
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize the OpenAI client
client = OpenAI()

def translate_audio(file_path, prompt):
    """
    Translates audio to English using OpenAI's Whisper model.

    Args:
        file_path (str): The path to the audio file.
        prompt (str): A prompt to guide the model's style or continue a previous audio segment.

    Returns:
        str: The translated text.
    """
    if not os.path.exists(file_path):
        return f"Error: Audio file not found at {file_path}"

    try:
        with open(file_path, "rb") as audio_file:
            translation = client.audio.translations.create(
                model="whisper-1",
                file=audio_file,
                prompt=prompt
            )
        return translation.text
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__": 
    # TODO:  Implement system-wide recording via hotkey.
    # TODO:  Implement translation via config options.
    # TODO:  Implement rolling queue (fixed size or optionally infinite.) for saving recent audio files for retrying transcription..
    # TODO:  Implement retry logic for failed transcriptions.
    # TODO:  Implement intelligent autopaste & prepending of space character  
    # TODO:  Implement specialized words list that will be injected in the priming prompt.
    # TODO:  Implement silent audio detection and cancellation.
    # TODO:  Implement continuation of previous recent request and context of incomplete sentences.
    # TODO:  Implement well-designed on-screen indicator for user feedback, a la WhisperFlow.
    # TODO:  Implement slick translation as a plus tier feature.
    
    
    # IMPORTANT: Replace this with the actual path to your audio file.
    # The audio file should be in a supported format (e.g., m4a, mp3, mp4, mpeg, mpga, wav, webm).
    audio_file_path = "test/test1-paris.m4a"

    # A custom primingprompt to guide the translation.
    custom_prompt = "This is a technical discussion about artificial intelligence."

    print(f"Translating audio file: {audio_file_path}")
    print(f"With prompt: {custom_prompt}")
    print("-" * 20)

    translated_text = translate_audio(audio_file_path, custom_prompt)

    print("Translated Text:")
    print(translated_text)
