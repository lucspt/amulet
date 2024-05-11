import wave
import subprocess
import pyaudio
from gpiozero import Button, LED
from config import Config
import numpy as np
from numbers import Number


class AudioTools:
    __slots__ = (
        "channels",
        "sample_rate",
        "chunk",
        "format",
        "output_file",
        "button",
        "wake_signal",
    )

    def __init__(self, button: Button, led: LED):
        params = self.p.get_default_input_device_info()
        self.channels = int(params["maxInputChannels"])
        self.sample_rate = int(params["defaultSampleRate"])
        self.chunk = 128  # TODO: FIGURE OUT A GOOD NUMBER
        self.format = pyaudio.paInt16
        button.when_pressed = self.record_and_write
        config = Config()
        self.output_file = config.audio_input_file
        self.wake_signal = config.wake_signal_audio
        # self.led = led
        
    def get_rms(self, buffer: bytes):
        audio = np.frombuffer(buffer, dtype=np.int16).astype(np.float32)
        rms = np.sqrt(np.mean(np.square(audio)))
        return rms
    
    def rms_to_db(self, rms: Number):
        return 20 * np.log10(rms / 32768.0)

    def get_db(self, audio_bytes: bytes):
        rms = self.get_rms(audio_bytes)
        return self.rms_to_db(rms)
        
    @property
    def p(self):
        return pyaudio.PyAudio()

    def write_audio(
        self, audio_bytes: bytes, channels: int, sample_rate: int, sample_width: int
    ) -> str:
        """Writes audio to an output file"""
        output_file = self.output_file
        with wave.open(output_file, "wb") as wf:
            wf.setnchannels(channels)
            wf.setframerate(sample_rate)
            wf.setsampwidth(sample_width)
            wf.writeframes(audio_bytes)
        return output_file

    def record_and_write(self, button: Button) -> str:
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
        audio_bytes = bytearray()
        record_step = sample_rate // chunk
        while is_pressed := button.value:
            for _ in range(record_step):
                audio_bytes.extend(stream.read(chunk))
        stream.stop_stream()
        stream.close()
        # self.led.off()
        p.terminate()
        self.write_audio(
            audio_bytes=bytes(audio_bytes),
            channels=channels,
            sample_rate=sample_rate,
            sample_width=p.get_sample_size(format),
        )

    def audio_playback(self, audio_file):
        subprocess.Popen(["mpg123", audio_file]).wait()
        
#using a buffer, it's slower though?   

# class AudioTools:
#     __slots__ = (
#         "channels",
#         "sample_rate",
#         "chunk",
#         "format",
#         "output_file",
#         "button",
#         "_buffer",
#         "wake_signal",
#     )

#     def __init__(self, button: Button, led: LED):
#         params = self.p.get_device_info_by_index(1)
#         self.channels = int(params["maxInputChannels"])
#         self.sample_rate = int(params["defaultSampleRate"])
#         self.chunk = 128  # TODO: FIGURE OUT A GOOD NUMBER?
#         self.format = pyaudio.paInt16
#         button.when_pressed = self.record
#         self.button = button
#         config = Config()
#         self.output_file = config.audio_input_file #write the recordings to model's entrypoint
#         self.wake_signal = config.wake_signal_audio
#         self.tts_format = config.tts_file_format
#         # self.led = led
#         self._buffer = BytesIO()

#     @property
#     def p(self):
#         return pyaudio.PyAudio()
    
#     @property 
#     def audio_bytes(self):
#         audio_bytes = self._buffer
#         self._buffer = BytesIO()
#         return audio_bytes

#     def write_audio(self, channels: int, sample_rate: int, sample_width: int) -> str:
#         """Writes audio to an output file"""
#         frames = self.audio_bytes.getvalue() #must get frames before writing to buffer
#         with wave.open(self._buffer, "wb") as wf:
#             wf.setnchannels(channels)
#             wf.setframerate(sample_rate)
#             wf.setsampwidth(sample_width)
#             wf.writeframes(frames)

#     def record(self, button: Button) -> str: #pragma: no cover; see tests/device/test_audio.py
#         """Records from microphone while the button is held down,
#         returns a resulting output audio file"""
#         self.audio_playback(self.wake_signal)
        
#         channels, sample_rate = self.channels, self.sample_rate
#         format, p, chunk = self.format, self.p, self.chunk
#         stream = p.open(
#             format=self.format,
#             channels=self.channels,
#             rate=sample_rate,
#             frames_per_buffer=self.chunk,
#             input=True,
#         )

#         audio_buffer = self._buffer
#         while is_pressed := button.value:
#             for _ in range(0, int(sample_rate / chunk)):
#                 audio_buffer.write(stream.read(chunk))
#         stream.stop_stream()
#         stream.close()
#         p.terminate()
#         self.write_audio(
#             channels=channels,
#             sample_rate=sample_rate,
#             sample_width=p.get_sample_size(format),
#         )
#         # led.off()
        
#     def audio_playback(self, audio_file: str) -> None:
#         subprocess.Popen(["mpg123", "-q", audio_file]).wait()
        
#     # def audio_playback(self, audio_buffer: BytesIO):
#     #     audio = AudioSegment.from_file(audio_buffer, format=self.tts_format)
#     #     play(audio)
        
         
# import numpy as np
# from numbers import Number
# from io import BytesIO

# class AudioRecording(BytesIO):
#     def __init__(self, name: str, *args, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.name = name

#     def get_rms(self, buffer: bytes):
#         audio = np.frombuffer(buffer, dtype=np.int16).astype(np.float32)
#         rms = np.sqrt(np.mean(np.square(audio)))
#         return rms
    
#     def rms_to_db(self, rms: Number):
#         return 20 * np.log10(rms / 32768.0)

#     def get_decibles(self, audio_bytes: bytes):
#         rms = self.get_rms(audio_bytes)
#         return self.rms_to_db(rms)
    
#     @property
#     def volume(self):
#         return self.get_decibles(self.getvalue())
    
# class AudioTools:
#     __slots__ = (
#         "channels",
#         "sample_rate",
#         "chunk",
#         "format",
#         "output_file",
#         "button",
#         "_buffer",
#         "wake_signal",
#         "tts_format",
#         "silence_threshold",
#         "sample_width",
#     )

#     def __init__(self, button: Button, led: LED):
#         # self.led = led
#         self.chunk = 128
#         config = Config()
#         self.button = button
#         format =  pyaudio.paInt16
#         self.format = format
#         p = self.p
#         self.sample_width = p.get_sample_size(format)
#         self.silence_threshold = -32.0
#         output_file = config.audio_input_file
#         self.output_file = output_file
#         button.when_pressed = self.record
#         self.wake_signal = config.wake_signal_audio
#         self.tts_format = config.tts_file_format
#         params = p.get_device_info_by_index(1)
#         self._buffer = AudioRecording(name=output_file)
#         self.channels = int(params["maxInputChannels"])
#         self.sample_rate = int(params["defaultSampleRate"])

#     @property
#     def p(self):
#         return pyaudio.PyAudio()
    
#     @property 
#     def audio_bytes(self):
#         audio_bytes = self._buffer
#         self.new_recording()
#         if audio_bytes.volume < self.silence_threshold:
#             return None
#         audio_bytes.seek(0)
#         return audio_bytes
    
#     def new_recording(self):
#         self._buffer = AudioRecording(name=self.output_file)
    
#     def write_audio(
#         self,
#         audio: bytes,
#         channels: int,
#         sample_rate: int,
#         sample_width: int
#     ) -> None:
#         """Writes audio to an output file"""
#         self._buffer.close()
#         self.new_recording()
#         with wave.open(self._buffer, "wb") as wf:
#             wf.setnchannels(channels)
#             wf.setframerate(sample_rate)
#             wf.setsampwidth(sample_width)
#             wf.writeframes(audio)


#     def record(self, button: Button) -> str: #pragma: no cover; see tests/device/test_audio.py
#         """Records from microphone while the button is held down,
#         returns a resulting output audio file"""
#         self.audio_playback(self.wake_signal)
        
#         channels, sample_rate = self.channels, self.sample_rate
#         format, p, chunk = self.format, self.p, self.chunk
#         stream = p.open(
#             format=format,
#             channels=channels,
#             rate=sample_rate,
#             frames_per_buffer=chunk,
#             input=True,
#         )

#         audio_buffer = self._buffer
#         record_step = sample_rate // chunk
#         while (is_pressed := button.value):
#             for _ in range(record_step):
#                 audio_buffer.write(stream.read(chunk))
#         stream.stop_stream() 
#         stream.close()
#         p.terminate()
#         # led.off()
#         self.write_audio(
#             audio=audio_buffer.getvalue(),
#             channels=channels,
#             sample_rate=sample_rate,
#             sample_width=p.get_sample_size(format),
#         )
        
#     def audio_playback(self, audio_file: str) -> None:
#         subprocess.run(["mpg123", "-q", audio_file])


