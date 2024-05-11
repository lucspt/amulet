import wave, subprocess
import pyaudio
from gpiozero import Button, LED
from multiprocessing import Queue
from config import Config
from io import BytesIO
# from pydub import AudioSegment
# from pydub.playback import play


class AudioTools:
    __slots__ = (
        "channels",
        "sample_rate",
        "chunk",
        "format",
        "output_file",
        "button",
        "wake_signal",
        "list",
        "flag",
        "_buffer"
        
    )

    def __init__(self, button: Button, led: LED, list):
        params = self.p.get_default_input_device_info()
        self.channels = int(params["maxInputChannels"])
        self.sample_rate = int(params["defaultSampleRate"])
        self.chunk = 128  # TODO: FIGURE OUT A GOOD NUMBER
        self.format = pyaudio.paInt16
        # button.when_pressed = self.record_and_write
        config = Config()
        self.output_file = config.audio_input_file
        self.wake_signal = config.wake_signal_audio
        self.list = list
        self.flag = 1
        self._buffer = BytesIO()
        # self.led = led

    @property
    def p(self):
        return pyaudio.PyAudio()

    def write_audio(
        self, audio_bytes: bytes, channels: int, sample_rate: int, sample_width: int
    ) -> str:
        """Writes audio to an output file"""
        buffer = BytesIO()
        with wave.open(buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setframerate(sample_rate)
            wf.setsampwidth(sample_width)
            wf.writeframes(audio_bytes)
        return buffer.getvalue()
        

    def record_and_write(self, duration) -> str:
        """Records from microphone while the button is held down,
        returns a resulting output audio file"""
        # self.led.on()
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

        count = 0
        while  count < duration:
            count += 1
            audio_bytes = bytearray()
            print(count, duration)
            for _ in range(0, int(sample_rate / chunk * 1.3)):
                audio_bytes.extend(stream.read(chunk))
            if audio_bytes:
                audio = self.write_audio(
                    audio_bytes=bytes(audio_bytes),
                    channels=channels,
                    sample_rate=sample_rate,
                    sample_width=p.get_sample_size(format),
                    )
            # if count > 0:
            #     audio = audio.split(b"fmt ")[-1]
                self.list.append(audio)
        stream.stop_stream()
        stream.close()
        p.terminate()
        # output_file = self.write_audio(
        #     audio_bytes=bytes(audio_bytes),
        #     channels=channels,
        #     sample_rate=sample_rate,
        #     sample_width=p.get_sample_size(self.format),
        # )
        # self.led.off()
        self.flag = 0
        return "done"

    def audio_playback(self, audio_file):
        subprocess.Popen(["mpg123", audio_file]).wait()