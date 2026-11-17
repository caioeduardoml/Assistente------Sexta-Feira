"""Motor de reconhecimento de voz offline (Vosk + sounddevice) com medicao de nivel de audio."""

import array
import json
import math
import os
import queue
import threading
from typing import Callable, Optional

from .commands import CommandProcessor, CommandResult, send_notification
from .config import BLOCK_SIZE, SAMPLE_RATE, LanguageProfile


class VoiceEngine:
    """Captura audio do microfone em background e processa comandos via Vosk."""

    def __init__(
        self,
        profile: LanguageProfile,
        processor: CommandProcessor,
        model_path: Optional[str] = None,
        on_state_change: Optional[Callable[[str, str], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        on_partial_text: Optional[Callable[[str], None]] = None,
        on_command_result: Optional[Callable[[CommandResult], None]] = None,
        on_unavailable: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.profile = profile
        self.processor = processor
        self.model_path = model_path or profile.model_path
        self.on_state_change = on_state_change
        self.on_audio_level = on_audio_level
        self.on_partial_text = on_partial_text
        self.on_command_result = on_command_result
        self.on_unavailable = on_unavailable

        self._audio_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._muted = False
        self._force_command_mode = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="LucyVoiceThread", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        self._audio_queue.put(None)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)

    def set_muted(self, muted: bool) -> None:
        self._muted = muted
        if muted:
            self._emit_level(0.0)
            self._emit_state("idle", "Microfone silenciado" if self.profile.code == "pt" else "Microphone muted")
        else:
            self._emit_state("idle", self.profile.messages["listening_wake"])

    def trigger_command_mode(self) -> None:
        """Ativa o modo de comando diretamente sem precisar da palavra de ativacao."""
        self._force_command_mode = True
        self._emit_state("listening", self.profile.messages["listening_cmd"])

    def _emit_state(self, state: str, message: str) -> None:
        if self.on_state_change:
            self.on_state_change(state, message)

    def _emit_level(self, level: float) -> None:
        if self.on_audio_level:
            self.on_audio_level(level)

    @staticmethod
    def _compute_rms(pcm_bytes: bytes) -> float:
        if not pcm_bytes:
            return 0.0
        samples = array.array("h")
        samples.frombytes(pcm_bytes)
        if not samples:
            return 0.0
        sum_sq = sum(s * s for s in samples)
        rms = math.sqrt(sum_sq / len(samples))
        # Normaliza 16-bit PCM para faixa aproximada [0.0, 1.0]
        return min(1.0, rms / 6000.0)

    def _run(self) -> None:
        try:
            import sounddevice as sd
            from vosk import KaldiRecognizer, Model
        except ImportError as exc:
            reason = f"Dependencia de audio ausente: {exc}"
            if self.on_unavailable:
                self.on_unavailable(reason)
            return

        if not os.path.exists(self.model_path):
            reason = f"Modelo Vosk nao encontrado em: {self.model_path}"
            if self.on_unavailable:
                self.on_unavailable(reason)
            return

        self._emit_state("processing", "Carregando modelo Vosk..." if self.profile.code == "pt" else "Loading Vosk model...")

        try:
            model = Model(self.model_path)
            vocab = list(self.profile.flat_commands.keys()) + list(self.profile.wake_words)
            recognizer = KaldiRecognizer(model, SAMPLE_RATE, json.dumps(vocab))
            recognizer.SetWords(True)
        except Exception as exc:
            if self.on_unavailable:
                self.on_unavailable(f"Falha ao iniciar Vosk: {exc}")
            return

        def audio_callback(indata, frames, time_info, status):
            if self._stop_event.is_set() or self._muted:
                return
            data = bytes(indata)
            self._audio_queue.put(data)

        self._emit_state("idle", self.profile.messages["listening_wake"])
        send_notification(self.profile.app_name, self.profile.messages["online_title"], self.profile.messages["online_body"])

        try:
            with sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
                callback=audio_callback,
            ):
                command_mode = False
                while not self._stop_event.is_set():
                    try:
                        data = self._audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if data is None:
                        break
                    if self._muted:
                        continue

                    self._emit_level(self._compute_rms(data))

                    if self._force_command_mode:
                        command_mode = True
                        self._force_command_mode = False

                    if recognizer.AcceptWaveform(data):
                        result_json = json.loads(recognizer.Result())
                        text = result_json.get("text", "").strip()
                        if not text:
                            continue

                        if command_mode:
                            self._emit_state("processing", text)
                            cmd_result = self.processor.process(text)
                            if self.on_command_result:
                                self.on_command_result(cmd_result)
                            command_mode = False
                            if not cmd_result.should_exit:
                                self._emit_state("idle", self.profile.messages["listening_wake"])
                        else:
                            for wake in self.profile.wake_words:
                                if wake in text:
                                    command_mode = True
                                    self._emit_state("listening", self.profile.messages["listening_cmd"])
                                    send_notification(
                                        self.profile.app_name,
                                        "Lucy",
                                        self.profile.messages["listening_cmd"],
                                        "normal",
                                    )
                                    rest = text.split(wake, 1)[-1].strip()
                                    if rest:
                                        cmd_result = self.processor.process(rest)
                                        if self.on_command_result:
                                            self.on_command_result(cmd_result)
                                        command_mode = False
                                        if not cmd_result.should_exit:
                                            self._emit_state("idle", self.profile.messages["listening_wake"])
                                    break
                    else:
                        partial_json = json.loads(recognizer.PartialResult())
                        partial = partial_json.get("partial", "").strip()
                        if partial and self.on_partial_text:
                            self.on_partial_text(partial)
        except Exception as exc:
            if self.on_unavailable:
                self.on_unavailable(f"Erro no dispositivo de audio: {exc}")
