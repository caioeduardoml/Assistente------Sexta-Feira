"""Configuracoes, perfis de idioma e registro de comandos da assistente Lucy."""

from dataclasses import dataclass
import os
from typing import Dict, List, Tuple, Union

CommandAction = Union[List[str], str]

SAMPLE_RATE = 16000
BLOCK_SIZE = 4000
FUZZY_THRESHOLD = 80


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    name: str
    app_name: str
    model_path: str
    pid_file: str
    wake_words: Tuple[str, ...]
    commands_grouped: Dict[Tuple[str, ...], CommandAction]
    messages: Dict[str, str]

    @property
    def flat_commands(self) -> Dict[str, CommandAction]:
        return {
            phrase: action
            for phrases, action in self.commands_grouped.items()
            for phrase in phrases
        }


PT_PROFILE = LanguageProfile(
    code="pt",
    name="Portugues (BR)",
    app_name="Lucy - Sexta-Feira",
    model_path=os.environ.get(
        "LUCY_MODEL_PT",
        os.path.expanduser("~/.config/hypr/scripts/model"),
    ),
    pid_file="/tmp/lucy_pt.pid",
    wake_words=("lucy", "luci", "sexta-feira", "sexta feira"),
    commands_grouped={
        # Abrir aplicativos
        ("abrir vscode", "abrir vs code", "abrir codigo"): ["code", "--new-window"],
        ("abrir firefox", "abrir faiarfox", "abrir raposa"): ["firefox"],
        ("abrir discord canary", "abrir discord", "abrir discordi canari", "abrir chat"): ["discord-canary"],
        ("abrir gimp", "abrir gimpi", "abrir editor de imagem"): ["gimp"],
        ("abrir brave", "abrir breive", "abrir breve"): ["brave"],
        ("abrir terminal", "abrir o terminal", "abrir kitty"): ["kitty"],
        ("abrir antigravity",): ["antigravity"],
        # Fechar e gerenciar janelas (Hyprland)
        ("fechar vscode", "fechar vs code"): ["hyprctl", "dispatch", "closewindow", "class:^(code)$"],
        ("fechar firefox", "fechar faiarfox", "fechar raposa"): ["hyprctl", "dispatch", "closewindow", "class:^(firefox)$"],
        ("fechar discord canary", "fechar discord", "fechar chat"): ["hyprctl", "dispatch", "closewindow", "class:^(discord-canary)$"],
        ("fechar gimp", "fechar gimpi", "fechar editor de imagem"): ["hyprctl", "dispatch", "closewindow", "class:^(gimp)$"],
        ("fechar brave", "fechar breive", "fechar breve"): ["hyprctl", "dispatch", "closewindow", "class:^(brave-browser)$"],
        ("fechar terminal", "fechar kitty"): ["hyprctl", "dispatch", "closewindow", "class:^(kitty)$"],
        ("fechar janela", "fechar programa", "matar processo"): ["hyprctl", "dispatch", "killactive"],
        ("tela cheia", "maximizar", "janela inteira"): ["hyprctl", "dispatch", "fullscreen", "0"],
        # Controle de midia
        ("tocar musica", "colocar uma musica", "abrir spotify", "tocar esbofitai"): [
            "sh",
            "-c",
            "brave --app=https://open.spotify.com & sleep 3 && playerctl play",
        ],
        ("pausar musica", "parar musica", "pause", "pausa"): ["playerctl", "pause"],
        ("continuar musica", "play na musica", "play", "plei"): ["playerctl", "play"],
        ("proxima musica", "pular musica", "proxima", "pular", "passar musica"): ["playerctl", "next"],
        ("musica anterior", "voltar musica", "anterior"): ["playerctl", "previous"],
        # Controle de volume (WirePlumber / PipeWire)
        ("aumentar volume", "aumentar o som", "mais alto", "subir volume"): [
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "10%+",
        ],
        ("diminuir volume", "diminuir o som", "mais baixo", "abaixar volume"): [
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "10%-",
        ],
        ("mutar", "mutar o som", "tirar o som", "desmutar", "mudo"): [
            "wpctl",
            "set-mute",
            "@DEFAULT_AUDIO_SINK@",
            "toggle",
        ],
        # Comandos internos da assistente
        ("que horas sao", "horas", "me diga as horas"): "INTERNAL:TIME",
        ("ajuda", "comandos", "o que voce faz"): "INTERNAL:HELP",
        ("fechar assistente", "desligar assistente", "desligar", "tchau", "encerrar"): "INTERNAL:EXIT",
    },
    messages={
        "online_title": "Lucy Online",
        "online_body": "Assistente inicializada com sucesso.",
        "listening_wake": "Aguardando gatilho (Lucy / Sexta-Feira)...",
        "listening_cmd": "Estou ouvindo... Diga o comando.",
        "executing": "Executando: {cmd}",
        "not_understood": "Nao entendi: '{text}'",
        "shutdown": "Encerrando assistente. Ate mais!",
        "text_only": "Modo texto ativo (microfone ou modelo Vosk indisponivel).",
        "time_reply": "Agora sao {time}.",
        "help_reply": "Posso abrir/fechar apps (terminal, firefox, vscode, brave, discord, gimp), controlar midia, volume e janelas do Hyprland.",
    },
)

EN_PROFILE = LanguageProfile(
    code="en",
    name="English (US)",
    app_name="Lucy - Friday",
    model_path=os.environ.get(
        "LUCY_MODEL_EN",
        os.path.expanduser("~/.config/hypr/scripts/model_en"),
    ),
    pid_file="/tmp/lucy_en.pid",
    wake_words=("lucy", "friday", "hey friday"),
    commands_grouped={
        # Open applications
        ("open vscode", "open vs code", "open code", "launch vscode"): ["code", "--new-window"],
        ("open firefox", "launch firefox", "run firefox"): ["firefox"],
        ("open brave", "launch brave"): ["brave"],
        ("open antigravity", "launch antigravity", "open anti gravity"): ["antigravity"],
        ("open gimp", "launch gimp"): ["gimp"],
        ("open cava", "launch cava"): ["kitty", "cava"],
        ("open discord", "launch discord"): ["discord-canary"],
        ("open terminal", "launch terminal", "open kitty", "terminal"): ["kitty"],
        # Window management (Hyprland)
        ("close vscode", "close vs code", "close code"): ["hyprctl", "dispatch", "closewindow", "class:^(code)$"],
        ("close firefox", "kill firefox"): ["hyprctl", "dispatch", "closewindow", "class:^(firefox)$"],
        ("close discord", "kill discord"): ["hyprctl", "dispatch", "closewindow", "class:^(discord-canary)$"],
        ("close brave", "kill brave"): ["hyprctl", "dispatch", "closewindow", "class:^(brave-browser)$"],
        ("close cava", "kill cava"): ["hyprctl", "dispatch", "closewindow", "class:^(cava)$"],
        ("close antigravity", "kill antigravity"): ["hyprctl", "dispatch", "closewindow", "class:^(antigravity)$"],
        ("close gimp", "kill gimp"): ["hyprctl", "dispatch", "closewindow", "class:^(gimp)$"],
        ("close terminal", "close kitty", "kill terminal"): ["hyprctl", "dispatch", "closewindow", "class:^(kitty)$"],
        ("close window", "close program", "kill window", "kill active"): ["hyprctl", "dispatch", "killactive"],
        ("fullscreen", "maximize", "toggle fullscreen"): ["hyprctl", "dispatch", "fullscreen", "0"],
        # Media control
        ("play spotify", "open spotify"): [
            "sh",
            "-c",
            "brave --app=https://open.spotify.com & sleep 3 && playerctl play",
        ],
        ("pause music", "stop music", "pause", "stop"): ["playerctl", "pause"],
        ("resume music", "continue music", "play", "resume", "play music"): ["playerctl", "play"],
        ("next music", "next song", "next", "skip music", "skip"): ["playerctl", "next"],
        ("previous music", "previous song", "previous"): ["playerctl", "previous"],
        # Volume control
        ("volume up", "louder", "increase volume", "raise volume"): [
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "10%+",
        ],
        ("volume down", "quieter", "decrease volume", "lower volume"): [
            "wpctl",
            "set-volume",
            "@DEFAULT_AUDIO_SINK@",
            "10%-",
        ],
        ("mute", "unmute", "mute audio", "toggle mute"): [
            "wpctl",
            "set-mute",
            "@DEFAULT_AUDIO_SINK@",
            "toggle",
        ],
        # Internal assistant commands
        ("what time is it", "time", "tell me the time"): "INTERNAL:TIME",
        ("help", "commands", "what can you do"): "INTERNAL:HELP",
        ("close assistant", "shutdown assistant", "turn off", "goodbye", "exit"): "INTERNAL:EXIT",
    },
    messages={
        "online_title": "Lucy Online",
        "online_body": "Assistant initialized successfully.",
        "listening_wake": "Waiting for wake word (Lucy / Friday)...",
        "listening_cmd": "Listening... Say your command.",
        "executing": "Executing: {cmd}",
        "not_understood": "Did not understand: '{text}'",
        "shutdown": "Shutting down assistant. See you later!",
        "text_only": "Text mode active (microphone or Vosk model unavailable).",
        "time_reply": "It is currently {time}.",
        "help_reply": "I can open/close apps (terminal, firefox, vscode, brave, discord, gimp), control media, volume, and Hyprland windows.",
    },
)

PROFILES: Dict[str, LanguageProfile] = {
    "pt": PT_PROFILE,
    "en": EN_PROFILE,
}


def get_profile(lang: str) -> LanguageProfile:
    return PROFILES.get(lang.lower(), PT_PROFILE)
