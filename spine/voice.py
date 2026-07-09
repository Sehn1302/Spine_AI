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

from cuda_paths import ensure_cuda_dll_path

ensure_cuda_dll_path()
from faster_whisper import WhisperModel

from host_capabilities import find_enhanced_audio_device


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
            marker = ""
            if i == default_in:
                marker += " [DEFAULT]"
            if _is_wireless_device(dev["name"]):
                marker += " [WIRELESS]"
            try:
                from host_capabilities import _is_enhanced_audio_device
                if _is_enhanced_audio_device(dev["name"]):
                    marker += " [ENHANCED]"
            except ImportError:
                pass
            lines.append(f"  [{i}] {dev['name']}{marker}")

    lines.append("")
    lines.append("OUTPUT (speakers / headphones):")
    for i, dev in enumerate(sd.query_devices()):
        if dev["max_output_channels"] > 0:
            marker = ""
            if i == default_out:
                marker += " [DEFAULT]"
            if _is_wireless_device(dev["name"]):
                marker += " [WIRELESS]"
            try:
                from host_capabilities import _is_enhanced_audio_device
                if _is_enhanced_audio_device(dev["name"]):
                    marker += " [ENHANCED]"
            except ImportError:
                pass
            lines.append(f"  [{i}] {dev['name']}{marker}")

    lines.append("")
    lines.append("Spine auto-picks [ENHANCED] noise-cancelling mics and [WIRELESS] Bluetooth devices.")
    lines.append("Set input_device / output_device in spine/config.yaml to pin a specific index.")
    return "\n".join(lines)


_BUILTIN_MARKERS = (
    "realtek",
    "microphone array",
    "intel smart",
    "internal",
    "webcam",
    "amd audio",
    "conexant",
    "dolby",
    "speaker (",
    "speakers (",
)

_WIRELESS_MARKERS = (
    "bluetooth",
    "hands-free",
    "headset",
    "headphones",
    "earbuds",
    "earphone",
    "airpods",
    "buds",
    "a2dp",
    "ag audio",
    "hfp",
    "wh-",
    "bt ",
    "wireless",
)

_PROFILE_SUFFIXES = (
    " hands-free ag audio",
    " hands-free",
    " stereo",
    " a2dp",
    " headphones",
    " headset",
    " ag audio",
    " hfp",
)


def _frame_rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio**2))) if audio.size else 0.0


def _trim_to_speech(audio: np.ndarray, sample_rate: int, *, threshold: float = 0.012) -> np.ndarray:
    """Trim silence edges so Whisper only processes actual speech."""
    frame_len = max(1, int(sample_rate * 0.025))
    if audio.size <= frame_len:
        return audio

    speech_starts: list[int] = []
    for start in range(0, len(audio) - frame_len + 1, frame_len):
        if _frame_rms(audio[start : start + frame_len]) >= threshold:
            speech_starts.append(start)

    if not speech_starts:
        return audio

    pad = int(sample_rate * 0.08)
    begin = max(0, speech_starts[0] - pad)
    end = min(len(audio), speech_starts[-1] + frame_len + pad)
    return audio[begin:end]


def _has_speech(audio: np.ndarray, *, threshold: float) -> bool:
    if audio.size == 0:
        return False
    peak = float(np.max(np.abs(audio)))
    rms = _frame_rms(audio)
    return peak >= threshold or rms >= threshold * 0.6


def _is_builtin_device(name: str) -> bool:
    lowered = name.lower()
    return any(marker in lowered for marker in _BUILTIN_MARKERS)


def _is_wireless_device(name: str) -> bool:
    lowered = name.lower()
    if _is_builtin_device(lowered):
        return False
    return any(marker in lowered for marker in _WIRELESS_MARKERS)


def _device_base_name(name: str) -> str:
    lowered = name.lower().strip()
    for suffix in _PROFILE_SUFFIXES:
        if lowered.endswith(suffix):
            lowered = lowered[: -len(suffix)].strip()
    return lowered


def _is_hands_free_profile(name: str) -> bool:
    lowered = name.lower()
    return "hands-free" in lowered or "hfp" in lowered or "ag audio" in lowered


def _score_wireless_device(name: str, *, kind: str) -> int | None:
    """Score wireless endpoints; higher is better. None = not a wireless candidate."""
    lowered = name.lower()
    if _is_builtin_device(lowered):
        return None
    if not _is_wireless_device(lowered):
        return None

    score = 1
    if "bluetooth" in lowered:
        score += 2

    if kind == "input":
        # Stereo / A2DP mics transcribe far better than HFP hands-free.
        if "stereo" in lowered and not _is_hands_free_profile(lowered):
            score += 10
        if "headphones" in lowered and not _is_hands_free_profile(lowered):
            score += 6
        if _is_hands_free_profile(lowered):
            score -= 6
    else:
        if "stereo" in lowered or "a2dp" in lowered or "headphones" in lowered:
            score += 8
        if _is_hands_free_profile(lowered):
            score -= 8

    return score


def find_wireless_device(kind: str, *, match_name: str | None = None) -> int | None:
    """Pick any connected Bluetooth / wireless mic or speaker."""
    matches: list[tuple[int, int]] = []
    target = _device_base_name(match_name) if match_name else None

    for i, dev in enumerate(sd.query_devices()):
        channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
        if channels <= 0:
            continue

        score = _score_wireless_device(dev["name"], kind=kind)
        if score is None:
            continue

        if target:
            base = _device_base_name(dev["name"])
            if base == target or target in base or base in target:
                score += 12

        matches.append((score, i))

    if not matches:
        return None
    matches.sort(reverse=True)
    return matches[0][1]


def _default_device_index(kind: str) -> int:
    return sd.default.device[0 if kind == "input" else 1]


def _pick_non_hands_free_default(kind: str) -> int | None:
    """Prefer PC speakers / laptop mic over Bluetooth HFP profiles."""
    default_idx = _default_device_index(kind)
    try:
        default_name = sd.query_devices(default_idx)["name"]
        if not _is_hands_free_profile(default_name):
            return default_idx
    except Exception:
        pass

    best: tuple[int, int] | None = None
    for i, dev in enumerate(sd.query_devices()):
        channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
        if channels <= 0:
            continue
        name = dev["name"]
        if _is_hands_free_profile(name):
            continue
        score = 0
        if _is_builtin_device(name):
            score += 5
        if kind == "output" and ("speaker" in name.lower() or "realtek" in name.lower()):
            score += 4
        if kind == "input" and ("microphone array" in name.lower() or "realtek" in name.lower()):
            score += 4
        if _is_wireless_device(name) and not _is_hands_free_profile(name):
            score += 3
        if best is None or score > best[0]:
            best = (score, i)
    return best[1] if best else default_idx


def resolve_device(
    device: int | str | None,
    *,
    kind: str,
    auto_bluetooth: bool = False,
    paired_with: str | None = None,
) -> int | None:
    """Resolve device from index, name substring, auto-wireless, or system default."""
    if isinstance(device, int) or (isinstance(device, str) and device.isdigit()):
        return int(device)

    if device not in (None, "", "default"):
        name = str(device).lower()
        for i, dev in enumerate(sd.query_devices()):
            channels = dev["max_input_channels"] if kind == "input" else dev["max_output_channels"]
            if channels > 0 and name in dev["name"].lower():
                return i
        return None

    if auto_bluetooth:
        default_idx = sd.default.device[0 if kind == "input" else 1]
        default_name = sd.query_devices(default_idx)["name"]
        if _is_wireless_device(default_name):
            return default_idx

        wireless = find_wireless_device(kind, match_name=paired_with)
        if wireless is not None:
            return wireless

    return None


def resolve_audio_pair(
    input_pref: int | str | None,
    output_pref: int | str | None,
    *,
    auto_bluetooth: bool,
    prefer_enhanced_audio: bool = True,
) -> tuple[int | None, int | None]:
    """Resolve mic + speaker, using host noise cancellation and wireless when available."""
    explicit_input = input_pref not in (None, "", "default")
    explicit_output = output_pref not in (None, "", "default")

    input_device = resolve_device(input_pref, kind="input", auto_bluetooth=auto_bluetooth)
    if input_device is None and prefer_enhanced_audio and not explicit_input:
        input_device = find_enhanced_audio_device("input")

    input_name = sd.query_devices(input_device)["name"] if input_device is not None else None

    output_device = resolve_device(
        output_pref,
        kind="output",
        auto_bluetooth=auto_bluetooth,
        paired_with=input_name,
    )
    if output_device is None and prefer_enhanced_audio and not explicit_output:
        output_device = find_enhanced_audio_device("output")

    if output_device is None and auto_bluetooth and input_name:
        output_device = find_wireless_device("output", match_name=input_name)

    if input_device is None and auto_bluetooth and output_device is not None:
        output_name = sd.query_devices(output_device)["name"]
        input_device = find_wireless_device("input", match_name=output_name)

    if input_device is None and auto_bluetooth and not explicit_input:
        input_device = find_wireless_device("input")

    if output_device is not None:
        try:
            if _is_hands_free_profile(sd.query_devices(output_device)["name"]):
                output_device = _pick_non_hands_free_default("output")
        except Exception:
            output_device = _pick_non_hands_free_default("output")

    if input_device is not None:
        try:
            if _is_hands_free_profile(sd.query_devices(input_device)["name"]):
                alt = find_enhanced_audio_device("input") if prefer_enhanced_audio else None
                if alt is None:
                    alt = _pick_non_hands_free_default("input")
                if alt is not None:
                    input_device = alt
        except Exception:
            pass

    return input_device, output_device


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
        min_peak: float = 0.006,
        passive_min_peak: float = 0.012,
        auto_bluetooth: bool = True,
        prefer_enhanced_audio: bool = True,
        noise_cancellation: bool = True,
        listen_mode: str = "continuous",
        silence_stop_seconds: float = 1.0,
        max_utterance_seconds: float = 25.0,
        conversation_min_peak: float = 0.003,
        boot_use_default_mic: bool = True,
        on_state_change: Callable[[SpineState], None] | None = None,
    ) -> None:
        self.stt_model_name = stt_model
        self.stt_device = stt_device
        self.tts_voice = tts_voice
        self.record_seconds = record_seconds
        self.sleep_listen_seconds = sleep_listen_seconds
        self.min_peak = min_peak
        self.passive_min_peak = passive_min_peak
        self.conversation_min_peak = conversation_min_peak
        self.boot_use_default_mic = boot_use_default_mic
        self.listen_mode = listen_mode
        self.silence_stop_seconds = silence_stop_seconds
        self.max_utterance_seconds = max_utterance_seconds
        self.sample_rate = sample_rate
        self._input_pref = input_device
        self._output_pref = output_device
        self.auto_bluetooth = auto_bluetooth
        self.prefer_enhanced_audio = prefer_enhanced_audio
        self.noise_cancellation = noise_cancellation
        self.on_state_change = on_state_change
        self.state = SpineState.IDLE
        self._whisper: WhisperModel | None = None
        self._apply_devices()

    def _apply_devices(self) -> None:
        prev_in = getattr(self, "input_device", None)
        prev_out = getattr(self, "output_device", None)

        if self.boot_use_default_mic and self._input_pref in (None, "", "default"):
            self.input_device = _pick_non_hands_free_default("input")
            self.output_device = _pick_non_hands_free_default("output")
            if prev_in != self.input_device or prev_out != self.output_device:
                self._log_active_devices(verbose=True)
            return

        self.input_device, self.output_device = resolve_audio_pair(
            self._input_pref,
            self._output_pref,
            auto_bluetooth=self.auto_bluetooth,
            prefer_enhanced_audio=self.prefer_enhanced_audio
            if not (self.boot_use_default_mic and self._input_pref in (None, "", "default"))
            else False,
        )
        if prev_in != self.input_device or prev_out != self.output_device:
            self._log_active_devices(verbose=True)

    def refresh_devices(self) -> None:
        """Re-scan for newly connected Bluetooth / wireless audio devices."""
        prev_in = self.input_device
        prev_out = self.output_device

        input_pref = self._input_pref
        output_pref = self._output_pref
        prefer_enhanced = self.prefer_enhanced_audio

        if self.boot_use_default_mic and input_pref in (None, "", "default"):
            # Use Windows default unless it is low-quality BT hands-free.
            default_in = _pick_non_hands_free_default("input")
            default_out = _pick_non_hands_free_default("output")
            self.input_device = default_in
            self.output_device = default_out
            if prev_in != self.input_device or prev_out != self.output_device:
                print("Audio devices updated:")
                self._log_active_devices(verbose=True)
            return

        self.input_device, self.output_device = resolve_audio_pair(
            input_pref,
            output_pref,
            auto_bluetooth=self.auto_bluetooth,
            prefer_enhanced_audio=prefer_enhanced,
        )
        if prev_in != self.input_device or prev_out != self.output_device:
            print("Audio devices updated:")
            self._log_active_devices(verbose=True)

    def _log_active_devices(self, *, verbose: bool = True) -> None:
        in_idx = self.input_device if self.input_device is not None else sd.default.device[0]
        out_idx = self.output_device if self.output_device is not None else sd.default.device[1]
        try:
            in_name = sd.query_devices(in_idx)["name"]
            out_name = sd.query_devices(out_idx)["name"]
            logging.info("Voice input device: %s", in_name)
            logging.info("Voice output device: %s", out_name)
            if verbose:
                print(f"Microphone: {in_name}")
                print(f"Speaker:    {out_name}")
        except Exception as exc:
            logging.warning("Could not query audio devices: %s", exc)

    def _set_state(self, state: SpineState) -> None:
        if self.state == state:
            return
        self.state = state
        logging.info("Voice state: %s", state.value)
        if self.on_state_change:
            self.on_state_change(state)

    def _load_whisper(self, device: str) -> WhisperModel:
        ensure_cuda_dll_path()
        compute_type = "float16" if device == "cuda" else "int8"
        logging.info("Loading Whisper model '%s' on %s", self.stt_model_name, device)
        return WhisperModel(
            self.stt_model_name,
            device=device,
            compute_type=compute_type,
        )

    def _get_whisper(self) -> WhisperModel:
        if self._whisper is None:
            try:
                self._whisper = self._load_whisper(self.stt_device)
            except Exception as exc:
                if self.stt_device != "cpu":
                    logging.warning("Whisper CUDA failed (%s) — using CPU.", exc)
                    self.stt_device = "cpu"
                    self._whisper = self._load_whisper("cpu")
                else:
                    raise
        return self._whisper

    def _cuda_whisper_broken(self, exc: BaseException) -> bool:
        msg = str(exc).lower()
        return "cublas" in msg or "cuda" in msg or "cudnn" in msg

    def _fallback_whisper_cpu(self) -> None:
        logging.warning("Switching speech recognition to CPU (CUDA libraries missing).")
        self.stt_device = "cpu"
        self._whisper = None

    def _record_wav(
        self,
        seconds: int | None = None,
        *,
        min_peak: float | None = None,
        listening_state: bool = True,
    ) -> Path:
        duration = seconds if seconds is not None else self.record_seconds
        threshold = min_peak if min_peak is not None else self.min_peak

        if listening_state:
            self._set_state(SpineState.LISTENING)
        else:
            self._set_state(SpineState.SLEEPING)

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
        if not _has_speech(audio, threshold=threshold):
            raise ValueError("No speech detected.")

        if self.noise_cancellation:
            audio = _trim_to_speech(audio, self.sample_rate, threshold=threshold * 0.75)
            if not _has_speech(audio, threshold=threshold * 0.5):
                raise ValueError("No speech detected.")

        # Normalize quiet Bluetooth / enhanced mics
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak < 0.15:
            audio = audio * (0.15 / peak)

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

    def _audio_to_wav(self, audio: np.ndarray) -> Path:
        audio = np.squeeze(audio)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        if peak > 0 and peak < 0.12:
            audio = audio * (0.12 / peak)

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

    def _record_until_silence(
        self,
        *,
        speech_threshold: float,
        silence_seconds: float,
        max_seconds: float,
        listening_state: bool = True,
    ) -> np.ndarray:
        """Copilot-style: record while you speak, stop after a pause."""
        if listening_state:
            self._set_state(SpineState.LISTENING)

        chunk_sec = 0.08
        chunk_samples = int(self.sample_rate * chunk_sec)
        silence_chunks = int(silence_seconds / chunk_sec)
        max_chunks = int(max_seconds / chunk_sec)

        buffers: list[np.ndarray] = []
        speech_started = False
        silent_count = 0
        pre_roll: list[np.ndarray] = []
        pre_roll_max = 4

        for _ in range(max_chunks):
            chunk = sd.rec(
                chunk_samples,
                samplerate=self.sample_rate,
                channels=1,
                dtype="float32",
                device=self.input_device,
            )
            sd.wait()
            chunk = np.squeeze(chunk)

            if _has_speech(chunk, threshold=speech_threshold):
                if not speech_started:
                    buffers.extend(pre_roll)
                    speech_started = True
                silent_count = 0
                buffers.append(chunk)
            elif speech_started:
                silent_count += 1
                buffers.append(chunk)
                if silent_count >= silence_chunks:
                    break
            else:
                pre_roll.append(chunk)
                if len(pre_roll) > pre_roll_max:
                    pre_roll.pop(0)

        if not buffers:
            logging.info("No speech detected in %.0fs window (mic peak threshold %.4f)", max_seconds, speech_threshold)
            raise ValueError("No speech detected.")

        audio = np.concatenate(buffers)
        peak = float(np.max(np.abs(audio))) if audio.size else 0.0
        logging.info("Captured %.2fs audio, peak %.4f", len(audio) / self.sample_rate, peak)
        return audio

    def _transcribe(self, wav_path: Path) -> str:
        kwargs: dict = {
            "beam_size": 5,
            "language": "en",
            "vad_filter": False,
        }
        try:
            model = self._get_whisper()
            segments, info = model.transcribe(str(wav_path), **kwargs)
        except RuntimeError as exc:
            if self.stt_device != "cpu" and self._cuda_whisper_broken(exc):
                self._fallback_whisper_cpu()
                model = self._get_whisper()
                segments, info = model.transcribe(str(wav_path), **kwargs)
            else:
                raise
        text = " ".join(segment.text.strip() for segment in segments).strip()
        if not text:
            logging.info(
                "Transcription empty (duration %.2fs, language_prob %.2f)",
                getattr(info, "duration", 0.0),
                getattr(info, "language_probability", 0.0),
            )
        return text

    def _maybe_refresh_devices(self) -> None:
        """Re-scan audio only when wireless auto-pick is enabled."""
        if self.auto_bluetooth:
            self.refresh_devices()

    def listen(self) -> str:
        """Record fixed window, transcribe, return text."""
        wav_path: Path | None = None
        try:
            logging.info("Listening for %ds...", self.record_seconds)
            print(f"Listening ({self.record_seconds}s)...")
            wav_path = self._record_wav(listening_state=True, min_peak=self.min_peak)
            text = self._transcribe(wav_path)
            if not text:
                raise ValueError("Could not understand speech.")
            logging.info('Heard: "%s"', text)
            print(f'Heard: "{text}"')
            return text
        finally:
            if wav_path and wav_path.exists():
                wav_path.unlink(missing_ok=True)
            if self.state == SpineState.LISTENING:
                self._set_state(SpineState.IDLE)

    def listen_passive(self, seconds: int | None = None) -> str:
        """Short listen for wake phrase — ignores background noise."""
        self._maybe_refresh_devices()
        duration = seconds if seconds is not None else self.sleep_listen_seconds
        wav_path: Path | None = None
        try:
            self._set_state(SpineState.SLEEPING)
            wav_path = self._record_wav(
                duration,
                min_peak=self.passive_min_peak,
                listening_state=False,
            )
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

        self._maybe_refresh_devices()
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

            pygame.mixer.quit()
            played = False
            out_idx = self.output_device if self.output_device is not None else sd.default.device[1]
            try:
                out_name = sd.query_devices(out_idx)["name"]
                pygame.mixer.init(devicename=out_name)
                played = True
            except Exception as exc:
                logging.warning("Output device init failed (%s), using Windows default.", exc)
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
