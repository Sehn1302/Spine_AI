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
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"


class VoiceInterface:
    def __init__(
        self,
        stt_model: str = "base",
        stt_device: str = "cuda",
        tts_voice: str = "en-GB-RyanNeural",
        record_seconds: int = 5,
        sample_rate: int = 16000,
        on_state_change: Callable[[SpineState], None] | None = None,
    ) -> None:
        self.stt_model_name = stt_model
        self.stt_device = stt_device
        self.tts_voice = tts_voice
        self.record_seconds = record_seconds
        self.sample_rate = sample_rate
        self.on_state_change = on_state_change
        self.state = SpineState.IDLE
        self._whisper: WhisperModel | None = None

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

    def _record_wav(self) -> Path:
        self._set_state(SpineState.LISTENING)
        print(f"Listening for {self.record_seconds} seconds...")

        frames = sd.rec(
            int(self.record_seconds * self.sample_rate),
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
        )
        sd.wait()

        audio = np.squeeze(frames)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 0.01:
            raise ValueError("No speech detected. Please speak louder or check your microphone.")

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

    def listen(self) -> str:
        wav_path: Path | None = None
        try:
            wav_path = self._record_wav()
            model = self._get_whisper()
            segments, _ = model.transcribe(str(wav_path), beam_size=5, language="en")
            text = " ".join(segment.text.strip() for segment in segments).strip()

            if not text:
                raise ValueError("Could not understand speech. Please try again.")

            print(f'Heard: "{text}"')
            return text
        finally:
            if wav_path and wav_path.exists():
                wav_path.unlink(missing_ok=True)
            if self.state == SpineState.LISTENING:
                self._set_state(SpineState.IDLE)

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
