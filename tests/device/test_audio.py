import pytest
from root.device.audio import AudioTools
from config import Config
from gpiozero import Button, LED, Device
from gpiozero.pins.mock import MockFactory
import wave
from pathlib import Path


class TestableAudioTools(AudioTools):
    """Must override a function to prevent infinite loop when unit testing"""
    __test__ = False

    def record_and_write(self, duration: int) -> str:
        """Records from microphone while the button is held down,
        returns a resulting output audio file"""
        
        # self.output_file = "mock_input_query.wav"
        self.audio_playback(self.wake_signal)
        
        channels, sample_rate = (
            self.channels,
            self.sample_rate,
        )
        format, p, chunk = self.format, self.p, self.chunk
        stream = p.open(
            format=self.format,
            channels=self.channels,
            rate=sample_rate,
            frames_per_buffer=self.chunk,
            input=True,
        )
        audio_bytes = bytearray
        while count < duration:
            for _ in range(0, int(sample_rate / chunk)):
                audio_bytes.extend(stream.read(chunk))
            count += 1
        stream.stop_stream()
        stream.close()
        p.terminate()
        output_file = self.write_audio(
            audio=audio_bytes,
            channels=channels,
            sample_rate=sample_rate,
            sample_width=p.get_sample_size(format),
        )
        # led.off()
        return output_file

class TestAudioTools:
    @pytest.fixture(scope="class")
    def tools(self):
        Device.pin_factory = MockFactory()
        config = Config()
        audio_button = Button(config.audio_pin, pull_up=False)
        audio_button.when_released = lambda: print("Testing audio...")
        wake_led = LED(config.wake_led_pin)
        audio_tools = TestableAudioTools(button=audio_button, led=wake_led)
        return audio_tools
        
    def test_record(self, tools):
        audio_tools = tools
        audio_tools.record_and_write(duration=5)
        assert Path(audio_tools.output_file).is_file()
        
        
        
    