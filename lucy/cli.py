"""Ponto de entrada unificado (GUI e modo terminal/headless) para a assistente Lucy."""

import argparse
import sys
import threading
from typing import Optional

from .commands import CommandProcessor
from .config import get_profile
from .pid_lock import PidLock
from .voice import VoiceEngine


def run_headless(lang: str, model_path: Optional[str] = None) -> int:
    profile = get_profile(lang)
    stop_event = threading.Event()

    processor = CommandProcessor(
        profile,
        on_exit=stop_event.set,
        notify=True,
    )

    def on_unavailable(reason: str) -> None:
        print(f"[Erro] {reason}", file=sys.stderr)
        stop_event.set()

    def on_result(res) -> None:
        print(f"-> {res.reply} ({res.confidence:.0f}%)")
        if res.should_exit:
            stop_event.set()

    engine = VoiceEngine(
        profile=profile,
        processor=processor,
        model_path=model_path,
        on_state_change=lambda s, m: print(f"[{s.upper()}] {m}"),
        on_command_result=on_result,
        on_unavailable=on_unavailable,
    )

    engine.start()
    try:
        while not stop_event.wait(timeout=0.5):
            pass
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        engine.stop()
    return 0


def main(default_lang: str = "pt", argv: Optional[list] = None) -> int:
    parser = argparse.ArgumentParser(description="Assistente Virtual Lucy (Offline / Hyprland)")
    parser.add_argument(
        "--lang",
        choices=["pt", "en"],
        default=default_lang,
        help="Idioma da assistente (pt ou en)",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Caminho personalizado para a pasta do modelo Vosk",
    )
    parser.add_argument(
        "--no-gui",
        action="store_true",
        help="Executa apenas em modo terminal/daemon sem interface grafica",
    )
    args = parser.parse_args(argv)

    profile = get_profile(args.lang)
    lock = PidLock(profile.pid_file)
    if not lock.acquire():
        print(f"Erro: A assistente ja esta rodando em outra instancia ({profile.pid_file}).")
        return 1

    try:
        if args.no_gui:
            return run_headless(args.lang, args.model)

        from .gui import run_gui
        return run_gui(lang=args.lang, model_path=args.model)
    finally:
        lock.release()
