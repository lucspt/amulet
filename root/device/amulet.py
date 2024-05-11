from root.device.audio import AudioTools
from root.model.model import Model
from config import Config
from gpiozero import Button, LED
from io import BytesIO

class Amulet:
    __slots__ = ("model", "camera", "audio_tools")

    def __init__(self, savior_id: str):
        config = Config()
        amulet_tools = {
            "get_view": self.get_view,
            "reject_query": self.reject_query,
            "respond_to_user": self.respond
        }
        self.model = Model(savior_id=savior_id, amulet_tools=amulet_tools)
        audio_button = Button(config.audio_pin, pull_up=False)
        wake_led = LED(config.wake_led_pin)
        audio_button.when_released = self.handle_query
        self.image_file = config.image_input_file
        self.audio_tools = AudioTools(button=audio_button, led=wake_led)

    def adjust_volume(self):
        pass

    def display(self):
        """Outputs the appropriate graphic from the main display"""
        pass

    def reject_query(self):
        # blinks red
        pass

    def get_view(self) -> BytesIO:
        """Takes a picture for model"""
        image_file = BytesIO()
        image_file.name = self.image_file
        self.camera.capture(image_file, resize=(512, 512))
        return image_file
    
    def respond(self, response: str) -> None:
        self.audio_tools.audio_playback(response)

    def handle_query(self) -> None:
        """On release of the sensor, this function calls the model
        with the recorded audio and then plays back its response, if any
        """
        try:
            audio_file = self.audio_tools.output_file
            audio_output = self.model(audio_file=audio_file)
            print(self.model.current_thread)
            if audio_output:
                self.audio_tools.audio_playback(audio_output)
        except Exception:
            self.reject_query()
            
            

