from root.device.audio import AudioTools
from root.model.model import Model
from config import Config
from gpiozero import Button, LED


class Amulet:
    __slots__ = ("model", "camera", "audio_tools")

    def __init__(self, savior_id: str):
        config = Config()
        amulet_tools = {
            "get_view": self.get_view,
            "reject_query": self.reject_query,
        }
        self.model = Model(savior_id=savior_id, amulet_tools=amulet_tools)

        audio_button = Button(config.audio_pin, pull_up=False)
        audio_button.when_released = self.handle_query
        wake_led = LED(config.wake_signal_pin)
        self.audio_tools = AudioTools(button=audio_button, led=wake_led)
        self.image_input_file = config.image_input_file
        print(audio_button.when_pressed, audio_button.when_released, "AUDIO BTTN")

    def adjust_volume(self):
        pass

    def display(self):
        """Outputs the appropriate graphic from the main display"""
        pass

    def reject_query(self, error: Exception) -> None:
        # blinks red
        print("Query rejected", error)
        pass

    def get_view(self):
        """Takes a picture for model"""
        image_file = self.image_input_file
        self.camera.capture(image_file, "jpeg", resize=(512, 512))
        return image_file

    @staticmethod
    def _cleanup(files: list[str]) -> None:
        pass
        # [Path(f).unlink(missing_ok=True) for f in files]

    def handle_query(self: str) -> None:
        """On release of query sensor, this function calls the model
        with the query and then plays back the response, if any"""
        try:
            audio_file = self.audio_tools.output_file
            audio_output = self.model(audio_file=audio_file)
            print(self.model.current_thread)
            if audio_output:
                self.audio_tools.audio_playback(audio_output)
                self._cleanup([audio_file, audio_output])
        except Exception as e:
            self.reject_query(e)
