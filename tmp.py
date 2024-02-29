import wave, subprocess
import pyaudio
from gpiozero import Button, LED
from config import Config
from numbers import Number
from io import BytesIO
from typing import Callable
import numpy as np
         

class AudioRecording(BytesIO):
    def __init__(self, name: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.name = name

    def get_rms(self, buffer: bytes):
        audio = np.frombuffer(buffer, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(np.square(audio)))
        return rms 
    
    def rms_to_db(self, rms: Number):
        return 20 * np.log10(rms / 32768.0)

    def get_decibles(self, audio_bytes: bytes):
        rms = self.get_rms(audio_bytes)
        return self.rms_to_db(rms)
    
    @property
    def volume(self):
        return self.get_decibles(self.getvalue())
    
class TempAudioTools:
    __slots__ = (
        "channels",
        "sample_rate",
        "chunk",
        "format",
        "output_file",
        "button",
        "_buffer",
        "wake_signal",
        "tts_format",
        "silence_threshold",
        "sample_width",
    )

    def __init__(self, button: Button, led: LED):
        # self.led = led
        self.chunk = 128
        config = Config()
        self.button = button
        format =  pyaudio.paInt16
        self.format = format
        p = self.p
        self.sample_width = p.get_sample_size(format)
        self.silence_threshold = -32.0
        output_file = config.audio_input_file
        self.output_file = output_file
        button.when_pressed = self.record
        self.wake_signal = config.wake_signal_audio
        self.tts_format = config.tts_file_format
        params = p.get_device_info_by_index(1)
        self._buffer = AudioRecording(name=output_file)
        self.channels = int(params["maxInputChannels"])
        self.sample_rate = int(params["defaultSampleRate"])

    @property
    def p(self):
        return pyaudio.PyAudio()
    
    @property 
    def audio_bytes(self):
        audio_bytes = self._buffer
        self.new_recording()
        if audio_bytes.volume < self.silence_threshold:
            return None
        audio_bytes.seek(0)
        return audio_bytes
    
    def new_recording(self):
        self._buffer = AudioRecording(name=self.output_file)
    
    def write_audio(
        self,
        audio: bytes,
        channels: int,
        sample_rate: int,
        sample_width: int
    ) -> None:
        """Writes audio to an output file"""
        self._buffer.close()
        self.new_recording()
        with wave.open(self._buffer, "wb") as wf:
            wf.setnchannels(channels)
            wf.setframerate(sample_rate)
            wf.setsampwidth(sample_width)
            wf.writeframes(audio)


    def record(self, button: Button) -> str: #pragma: no cover; see tests/device/test_audio.py
        """Records from microphone while the button is held down,
        returns a resulting output audio file"""
        self.audio_playback(self.wake_signal)
        
        channels, sample_rate = self.channels, self.sample_rate
        format, p, chunk = self.format, self.p, self.chunk
        stream = p.open(
            format=format,
            channels=channels,
            rate=sample_rate,
            frames_per_buffer=chunk,
            input=True,
        )

        audio_buffer = self._buffer
        record_step = sample_rate // chunk
        while (is_pressed := button.value):
            for _ in range(record_step):
                audio_buffer.write(stream.read(chunk))
        stream.stop_stream() 
        stream.close()
        p.terminate()
        # led.off()
        self.write_audio(
            audio=audio_buffer.getvalue(),
            channels=channels,
            sample_rate=sample_rate,
            sample_width=p.get_sample_size(format),
        )
        
    def audio_playback(self, audio_file: str) -> None:
        subprocess.run(["mpg123", audio_file])
        
# from signal import pause
# def check():
#     audio_bytes = at.audio_bytes
#     if audio_bytes:
#         with wave.open("input_quer.wav", "wb") as wf:
#             wf.setnchannels(at.channels)
#             wf.setframerate(at.sample_rate)
#             wf.setsampwidth(2)
#             wf.writeframes(audio_bytes.getvalue())
#         print(audio_bytes.name, audio_bytes.read()[:20])
#     else: print("silence")

# button = Button(17, pull_up=False)
# button.when_released = check
# at = TempAudioTools(button=button, led=None)
# pause()