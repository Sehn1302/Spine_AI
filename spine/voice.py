"""Voice interface — speech-to-text and text-to-speech for Spine."""

from __future__ import annotations

import asyncio
import logging
import tempfile
import wave
from enum import Enum
from pathlib import Path
from typing import Callable

import edge_tts
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class SpineState(str, Enum):
    SLEEPING = "sleeping"
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


def list_audio_devices() -> str:
    """List available microphone and speaker devices."""
    lines = ["Audio devices:", ""]
    default_in, default_out = sd.default.device

    lines.append("INPUT (microphones):")
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_input_channels"] > 0:
            marker = " [DEFAULT]" if i == default_in else ""
            lines.append(f"  [{i}] {dev['name']}{marker}")

    lines.append("")
    lines.append("OUTPUT (speakers / headphones):")
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0:
            marker = " [DEFAULT]" if i == default_out else ""
            lines.append(f"  [{i}] {dev['name']}{marker}")

    lines.append("")
    lines.append("Set input_device / output_device in spine/config.yaml (index number).")
    lines.append("Or set your device as default in Windows Sound settings.")
    return "\n".join(lines)


def resolve_device(device: int | str | None, *, kind: str) -> int | None:
    """Resolve device from index, name substring, or None for system default."""
    if device is None or device == "" or device == "default":
        return None

    if isinstance(device, int) or (isinstance(device, str) and device.isdigit()):
        return int(device)

    name = str(device).lower()
    for i, dev in enumerate(sd.query_devices()):
        channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
        if channels > 0 and name in dev["name"].lower():
            return i
    return None


class VoiceInterface:
    def __init__(
        self,
        stt_model: str = "base",
        stt_device: str = "cuda",
        tts_voice: str = "en-GB-RyanNeural",
        record_seconds: int = 5,
        sample_rate: int = 16000,
        input_device: int | str | None = None,
        output_device: int | str | None = None,
        sleep_listen_seconds: int = 2,
        on_state_change: Callable[[SpineState], None] | None = None,
    ) -> None:
        self.stt_model_name = stt_model
        self.stt_device = stt_device
        self.tts_voice = tts_voice
        self.record_seconds = record_seconds
        self.sleep_listen_seconds = sleep_listen_seconds
        self.sample_rate = sample_rate
        self.input_device = resolve_device(input_device, kind="input")
        self.output_device = resolve_device(output_device, kind="output")
        self.on_state_change = on_state_change
        self.state = SpineState.IDLE
        self._whisper: WhisperModel | None = None
        self._log_active_devices()

    def _log_active_devices(self) -> None:
        in_idx = self.input_device if self.input_device is not None else sd.default.device[0]
        out_idx = self.output_device if self.output_device is not None else sd.default.device[1]
        try:
            in_name = sd.query_devices(in_idx)["name"]
            out_name = sd.query_devices(out_idx)["name"]
            logging.info("Voice input device: %s", in_name)
            logging.info("Voice output device: %s", out_name)
            print(f"Microphone: {in_name}")
            print(f"Speaker:    {out_name}")
        except Exception as exc:
            logging.warning("Could not query audio devices: %s", exc)

    def _set_state(self, state: SpineState) -> None:
        self.state = state
        logging.info("Voice state: %s", state.value)
        if self.on_state_change:
            self.on_state_change(state)

    def _get_whisper(self) -> WhisperModel:
        if self._whisper is None:
            compute_type = "float16" if self.stt_device == "cuda" else "int8"
            logging.info("Loading Whisper model '%s' on %s", self.stt_model_name, self.stt_device)
            self._whisper = WhisperModel(
                self.stt_model_name,
                device=self.stt_device,
                compute_type=compute_type,
            )
        return self._whisper

    def _record_wav(self, seconds: int | None = None) -> Path:
        duration = seconds if seconds is not None else self.record_seconds
        self._set_state(SpineState.LISTENING)

        frames = sd.rec(
            int(duration * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            device=self.input_device,
        )
        sd.wait()

        audio = np.squeeze(frames)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 0.01:
            raise ValueError("No speech detected.")

        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = Path(temp.name)
        temp.close()

        pcm = np.int16(np.clip(audio, -1.0, 1.0) * 32767)
        with wave.open(str(temp_path), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(self.sample_rate)
            handle.writeframes(pcm.tobytes())

        return temp_path

    def _transcribe(self, wav_path: Path) -> str:
        model = self._get_whisper()
        segments, _ = model.transcribe(str(wav_path), beam_size=5, language="en")
        return " ".join(segment.text.strip() for segment in segments).strip()

    def listen(self) -> str:
        print(f"Listening for {self.record_seconds} seconds...")
        wav_path: Path | None = None
        try:
            wav_path = self._record_wav()
            text = self._transcribe(wav_path)

            if not text:
                raise ValueError("Could not understand speech. Please try again.")

            print(f'Heard: "{text}"')
            return text
        finally:
            if wav_path and wav_path.exists():
                wav_path.unlink(missing_ok=True)
            if self.state == SpineState.LISTENING:
                self._set_state(SpineState.IDLE)

    def listen_passive(self, seconds: int | None = None) -> str:
        """Short listen for wake word — returns empty string on silence."""
        duration = seconds if seconds is not None else self.sleep_listen_seconds
        wav_path: Path | None = None
        try:
            self._set_state(SpineState.SLEEPING)
            wav_path = self._record_wav(duration)
            return self._transcribe(wav_path)
        except ValueError:
            return ""
        except Exception as exc:
            logging.debug("Passive listen: %s", exc)
            return ""
        finally:
            if wav_path and wav_path.exists():
                wav_path.unlink(missing_ok=True)
            if self.state == SpineState.SLEEPING:
                self._set_state(SpineState.SLEEPING)

    def sleeping(self) -> None:
        self._set_state(SpineState.SLEEPING)

    async def _speak_async(self, text: str, output_path: Path) -> None:
        communicate = edge_tts.Communicate(text, self.tts_voice)
        await communicate.save(str(output_path))

    def speak(self, text: str) -> None:
        if not text.strip():
            return

        self._set_state(SpineState.SPEAKING)
        temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        audio_path = Path(temp.name)
        temp.close()

        try:
            asyncio.run(self._speak_async(text, audio_path))
            self._play_audio(audio_path)
        finally:
            if audio_path.exists():
                audio_path.unlink(missing_ok=True)
            self._set_state(SpineState.IDLE)

    def _play_audio(self, path: Path) -> None:
        try:
            import pygame

            pygame.mixer.init()
            pygame.mixer.music.load(str(path))
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.wait(100)
            pygame.mixer.quit()
        except Exception as exc:
            logging.error("Audio playback failed: %s", exc)
            print(f"(Voice playback unavailable: {exc})")

    def thinking(self) -> None:
        self._set_state(SpineState.THINKING)
