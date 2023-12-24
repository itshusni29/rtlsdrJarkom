import io
import time
import threading
import numpy as np
from rtlsdr import RtlSdr
import sounddevice
import speech_recognition as sr
import scipy.signal as signal
import dearpygui.dearpygui as dpg
import color_theme as ct

class SpiritBox:
    def __init__(self):
        self.sdr = RtlSdr()
        self.Fs = 2.4e6
        self.F_offset = 250000
        self.sdr.gain = 'auto'
        self._looping = False
        self._sample_buffer = []
        self._text_buffer = ""
        self._manual_freq = None  # Variable to store manually set frequency

    @property
    def looping(self):
        return self._looping

    @property
    def text_buffer(self):
        b = self._text_buffer
        self._text_buffer = ""
        return b

    @property
    def sample_buffer(self):
        b = self._sample_buffer
        self._sample_buffer = []
        return b

    @property
    def Fs(self):
        return self.sdr.sample_rate

    @Fs.setter
    def Fs(self, value):
        self.sdr.sample_rate = value

    @property
    def current_freq(self):
        return self._manual_freq if self._manual_freq is not None else self.sdr.center_freq

    def set_manual_freq(self, freq):
        self._manual_freq = freq

    def get_samples(self, hold_time_sec):
        Fc = self.current_freq - self.F_offset
        self.sdr.center_freq = Fc

        samples_to_read = int((self.Fs * hold_time_sec) // 1024)
        return self.sdr.read_samples(samples_to_read * 1024)

    def get_samples_realtime(self, block_size=1024):
        return self.sdr.read_samples(block_size * 1024)

    def filter_samples(self, samples, bandwidth=200000, n_taps=64):
        x1 = np.array(samples).astype("complex64")
        fc1 = np.exp(-1.0j*2.0*np.pi*self.F_offset/self.Fs*np.arange(len(x1)))
        x2 = x1 * fc1

        lpf = signal.remez(n_taps, [0, bandwidth, bandwidth+(self.Fs/2-bandwidth)/4, self.Fs/2], [1, 0], Hz=self.Fs)
        x3 = signal.lfilter(lpf, 1.0, x2)
        dec_rate = int(self.Fs / bandwidth)
        x4 = x3[0::dec_rate]
        Fs_y = self.Fs/dec_rate
        f_bw = bandwidth
        dec_rate = int(self.Fs / f_bw)
        x4 = signal.decimate(x2, dec_rate)

        y5 = x4[1:] * np.conj(x4[:-1])
        x5 = np.angle(y5)

        d = Fs_y * 75e-6
        x = np.exp(-1/d)
        b = [1-x]
        a = [1, -x]
        x6 = signal.lfilter(b, a, x5)
        audio_freq = 48100.0
        dec_audio = int(Fs_y/audio_freq)
        Fs_audio = Fs_y / dec_audio
        x7 = signal.decimate(x6, dec_audio)

        x7 *= 10000 / np.max(np.abs(x7))
        return x7, Fs_audio

    def speech_recognition(self, samples, Fs_audio):
        byte_io = io.BytesIO(bytes())
        np.save(byte_io, samples)
        byte_io.seek(0)
        result_bytes = byte_io.read()
        audio_data = sr.AudioData(result_bytes, int(Fs_audio), 2)
        r = sr.Recognizer()
        text = r.recognize_sphinx(audio_data)
        if text:
            self._text_buffer += text

    def run_automatic_realtime(self, start_freq, end_freq, step_freq):
        self._looping = True
        current_freq = start_freq
        try:
            while self._looping and current_freq <= end_freq:
                if self._manual_freq is not None:
                    current_freq = self._manual_freq

                self.sdr.center_freq = current_freq - self.F_offset
                samples = self.get_samples_realtime()
                filtered_samples, Fs_audio = self.filter_samples(samples)

                self._sample_buffer.extend(filtered_samples)

                # Menggunakan blocking mode pada sounddevice.play agar buffer tidak terlalu cepat kosong
                sounddevice.play(filtered_samples.astype("int16"), Fs_audio, blocking=True, latency=0.1, blocksize=4096)
                
                current_freq += step_freq
        finally:
            self.stop()

    def run_manual(self):
        self._looping = True
        block_size = 1024  # Ukuran blok audio
        try:
            while self._looping:
                samples = self.get_samples_realtime(block_size)
                filtered_samples, Fs_audio = self.filter_samples(samples)

                self._sample_buffer.extend(filtered_samples)

                sounddevice.play(filtered_samples.astype("int16"), Fs_audio, blocking=True, latency=0.1)

        finally:
            self.stop()


    def stop(self):
        self._looping = False

    def close(self):
        self._looping = False
        self.sdr.close()

# GUI code
