from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv
import os
# import atexit

load_dotenv(".env")
     
@dataclass(slots=True)   
class Config:
    audio_pin = 17
    wake_led_pin = 4
    tts_speed = 1.075
    chat_temperature = 0.7
    max_vision_tokens = 130
    vision_temperature = 0.2
    tts_file_format = "mp3"
    wake_signal_audio = "dearearth.mp3"
    audio_input_file = "input_query.wav"
    data_dir = Path.cwd().parent / "data"
    image_input_file = "current_view.jpg"
    audio_output_file = "audio_response.mp3"
    greenhouse_gasses = ["co2", "ch4", "n2o"]
    api_data_version = os.environ.get("API_DATA_VERSION")
        
# @atexit.register
# def cleanup_files():
#     [Path(p).unlink() for p in ["input_query.wav", "audio_response.wav"]]