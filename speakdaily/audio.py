"""Microphone recording and playback. Fails softly when no audio device exists.

Recording uses sounddevice's raw stream (no numpy needed). Playback uses the
Windows sound player (winsound), or sounddevice on other systems.
"""
from __future__ import annotations

import sys
import threading
import time
import wave
from array import array
from pathlib import Path

SAMPLE_RATE = 16000

try:
    import sounddevice as sd
    AUDIO_OK = True
    AUDIO_ERROR = ""
except Exception as exc:            # missing PortAudio etc.
    sd = None
    AUDIO_OK = False
    AUDIO_ERROR = str(exc)

try:
    import winsound
except ImportError:
    winsound = None


class Recorder:
    def __init__(self):
        self._chunks: list[bytes] = []
        self._stream = None
        self._paused = False
        self.level = 0.0            # 0..1, for the mic meter
        self.error = ""

    def start(self) -> bool:
        if not AUDIO_OK:
            self.error = "Audio library not available."
            return False
        try:
            self._stream = sd.RawInputStream(samplerate=SAMPLE_RATE, channels=1,
                                             dtype="int16", callback=self._callback)
            self._stream.start()
            return True
        except Exception as exc:
            self.error = f"No microphone found ({exc})."
            self._stream = None
            return False

    def _callback(self, indata, frames, time_info, status):
        if self._paused:
            self.level = 0.0
            return
        data = bytes(indata)
        self._chunks.append(data)
        samples = array("h", data)
        if samples:
            peak = max(abs(min(samples)), abs(max(samples))) / 32768.0
            self.level = min(1.0, peak * 3)

    def pause(self, paused: bool) -> None:
        self._paused = paused

    @property
    def active(self) -> bool:
        return self._stream is not None

    def stop(self, path: Path | None) -> Path | None:
        """Stop recording and save to `path`. With path=None the audio is discarded."""
        if self._stream is None:
            return None
        try:
            self._stream.stop()
            self._stream.close()
        except Exception:
            pass
        self._stream = None
        chunks, self._chunks = self._chunks, []
        if not chunks or path is None:
            return None
        with wave.open(str(path), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(SAMPLE_RATE)
            wav.writeframes(b"".join(chunks))
        return path


class Player:
    def __init__(self):
        self.playing = False
        self.error = ""
        self._token = 0

    def play(self, path: Path, on_done=None) -> bool:
        length = duration_seconds(path)
        try:
            if winsound is not None:
                winsound.PlaySound(str(path), winsound.SND_FILENAME | winsound.SND_ASYNC)
            elif AUDIO_OK:
                with wave.open(str(path), "rb") as wav:
                    rate, raw = wav.getframerate(), wav.readframes(wav.getnframes())
                self._raw_play(raw, rate)
            else:
                self.error = "Audio library not available."
                return False
        except Exception as exc:
            self.error = f"Cannot play the recording ({exc})."
            return False
        self.playing = True
        self._token += 1
        token = self._token

        def wait():
            time.sleep(length + 0.2)
            if token == self._token and self.playing:
                self.playing = False
                if on_done:
                    on_done()
        threading.Thread(target=wait, daemon=True).start()
        return True

    def _raw_play(self, raw: bytes, rate: int):
        def run():
            with sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16") as out:
                out.write(raw)
        threading.Thread(target=run, daemon=True).start()

    def stop(self) -> None:
        self._token += 1
        if self.playing and winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        self.playing = False


def duration_seconds(path: Path) -> float:
    try:
        with wave.open(str(path), "rb") as wav:
            return wav.getnframes() / float(wav.getframerate())
    except (OSError, wave.Error, EOFError):
        return 0.0


def beep(widget=None) -> None:
    """Short two-tone sound when time is up."""
    if winsound is not None:
        def run():
            try:
                winsound.Beep(880, 180)
                winsound.Beep(660, 260)
            except Exception:
                pass
        threading.Thread(target=run, daemon=True).start()
    elif widget is not None:
        widget.bell()
