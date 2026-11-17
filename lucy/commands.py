"""Motor de correspondencia fuzzy e execucao de comandos da assistente Lucy."""

from dataclasses import dataclass
from datetime import datetime
import subprocess
from typing import Callable, Optional
from rapidfuzz import fuzz

from .config import FUZZY_THRESHOLD, LanguageProfile


@dataclass
class CommandResult:
    recognized: bool
    raw_text: str
    clean_text: str
    matched_phrase: Optional[str] = None
    confidence: float = 0.0
    reply: str = ""
    should_exit: bool = False
    error: Optional[str] = None


def send_notification(app_name: str, title: str, message: str, urgency: str = "low") -> None:
    try:
        subprocess.Popen(
            ["notify-send", "-a", app_name, "-u", urgency, title, message],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        pass


class CommandProcessor:
    """Interpreta texto falado ou digitado e executa a acao correspondente."""

    def __init__(
        self,
        profile: LanguageProfile,
        on_exit: Optional[Callable[[], None]] = None,
        notify: bool = True,
    ) -> None:
        self.profile = profile
        self.flat_commands = profile.flat_commands
        self.on_exit = on_exit
        self.notify = notify

    def set_profile(self, profile: LanguageProfile) -> None:
        self.profile = profile
        self.flat_commands = profile.flat_commands

    def clean_wake_words(self, text: str) -> str:
        cleaned = text.lower().strip()
        for wake in self.profile.wake_words:
            if cleaned.startswith(wake):
                cleaned = cleaned.replace(wake, "", 1).strip()
        return cleaned

    def process(self, raw_text: str) -> CommandResult:
        cleaned = self.clean_wake_words(raw_text)
        if not cleaned:
            return CommandResult(recognized=False, raw_text=raw_text, clean_text="")

        best_phrase = None
        best_score = 0.0

        for phrase in self.flat_commands.keys():
            score = float(fuzz.token_sort_ratio(phrase, cleaned))
            if score > best_score:
                best_score = score
                best_phrase = phrase

        if best_score < FUZZY_THRESHOLD or best_phrase is None:
            reply = self.profile.messages["not_understood"].format(text=cleaned)
            if self.notify:
                send_notification(self.profile.app_name, "Lucy", reply, "low")
            return CommandResult(
                recognized=False,
                raw_text=raw_text,
                clean_text=cleaned,
                matched_phrase=best_phrase,
                confidence=best_score,
                reply=reply,
            )

        action = self.flat_commands[best_phrase]

        if isinstance(action, str) and action.startswith("INTERNAL:"):
            kind = action.split(":", 1)[1]
            if kind == "EXIT":
                reply = self.profile.messages["shutdown"]
                if self.notify:
                    send_notification(self.profile.app_name, "Lucy", reply, "normal")
                if self.on_exit:
                    self.on_exit()
                return CommandResult(
                    recognized=True,
                    raw_text=raw_text,
                    clean_text=cleaned,
                    matched_phrase=best_phrase,
                    confidence=best_score,
                    reply=reply,
                    should_exit=True,
                )
            if kind == "TIME":
                now_str = datetime.now().strftime("%H:%M")
                reply = self.profile.messages["time_reply"].format(time=now_str)
                return CommandResult(
                    recognized=True,
                    raw_text=raw_text,
                    clean_text=cleaned,
                    matched_phrase=best_phrase,
                    confidence=best_score,
                    reply=reply,
                )
            if kind == "HELP":
                reply = self.profile.messages["help_reply"]
                return CommandResult(
                    recognized=True,
                    raw_text=raw_text,
                    clean_text=cleaned,
                    matched_phrase=best_phrase,
                    confidence=best_score,
                    reply=reply,
                )

        # Executa comando de sistema
        try:
            subprocess.Popen(
                action,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            reply = self.profile.messages["executing"].format(cmd=best_phrase)
            if self.notify:
                send_notification(self.profile.app_name, "Lucy", reply, "low")
            return CommandResult(
                recognized=True,
                raw_text=raw_text,
                clean_text=cleaned,
                matched_phrase=best_phrase,
                confidence=best_score,
                reply=reply,
            )
        except OSError as exc:
            err_msg = f"Erro ao executar '{best_phrase}': {exc}"
            return CommandResult(
                recognized=True,
                raw_text=raw_text,
                clean_text=cleaned,
                matched_phrase=best_phrase,
                confidence=best_score,
                reply=err_msg,
                error=str(exc),
            )
