#!/usr/bin/env python3
import os
import sys
import json
import queue
import subprocess
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from rapidfuzz import fuzz

# --- MODEL AND AUDIO CONFIGISTRATION ---
# Configurado para apontar para a sua pasta de modelo em inglês
MODEL_PATH = os.path.expanduser("~/.config/hypr/scripts/model_en")
SAMPLE_RATE = 16000  # Default sampling rate for Vosk

if not os.path.exists(MODEL_PATH):
    print(f"Error: English model not found in {MODEL_PATH}. Please download it first!")
    sys.exit(1)

# Queue to pass audio blocks from the listener thread to the processing loop
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """This function is called for each audio block captured by the mic"""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

# --- AUTOMATION AND COMMANDS (PURE ENGLISH) ---
COMANDOS_AGRUPADOS = {
    #--------- OPEN APPLICATIONS -------------------------------
    ("open vscode", "open vs code", "open code", "launch vscode"): ["code", "--new-window"],
    ("open firefox", "launch firefox", "run firefox"): ["firefox"],
    ("open brave", "launch brave"): ["brave"],
    ("open antigravity", "launch antigravity", "open anti gravity"): ["antigravity"],
    ("open gimp", "launch gimp"): ["gimp"],
    ("open cava", "launch cava"): ["kitty","cava"],
    ("open discord", "launch discord"): ["discord-canary"],
    ("open terminal", "launch terminal", "open kitty", "terminal"): ["kitty"],

    #------------------ WINDOW MANAGEMENT ------------------------------
    ("close vscode", "close vs code", "close code"): ["hyprctl", "dispatch", "closewindow", "class:^(code)$"],
    ("close firefox", "kill firefox"): ["hyprctl", "dispatch", "closewindow", "class:^(firefox)$"],
    ("close discord", "kill discord"): ["hyprctl", "dispatch", "closewindow", "class:^(discord-canary)$"],
    ("close brave", "kill brave"): ["hyprctl", "dispatch", "closewindow", "class:^(brave-browser)$"],
    ("close cava", "kill cava"): ["hyprctl", "dispatch", "closewindow", "class:^(cava)$"],
    ("close antigravity", "kill antigravity"): ["hyprctl", "dispatch", "closewindow", "class:^(brave-browser)$"],
    ("close gimp", "kill gimp"): ["hyprctl", "dispatch", "closewindow", "class:^(gimp)$"],
    ("close terminal", "close kitty", "kill terminal"): ["hyprctl", "dispatch", "closewindow", "class:^(kitty)$"],
    ("close window", "close program", "kill window", "kill active"): ["hyprctl", "dispatch", "killactive"],
    ("fullscreen", "maximize", "toggle fullscreen"): ["hyprctl", "dispatch", "fullscreen", "0"],
    
    # Media Control (Brave + Spotify Web App)
    ("pause music", "stop music", "pause", "stop"): ["playerctl", "pause"],
    ("resume music", "continue music", "play", "resume", "play music"): ["playerctl", "play"],
    ("next music", "next song", "next", "skip music", "skip"): ["playerctl", "next"],

    # --- AUDIO VOLUME (WIREPLUMBER / PIPEWIRE) ---
    ("volume up", "louder", "increase volume", "raise volume"): ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"],
    ("volume down", "quieter", "decrease volume", "lower volume"): ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"],
    ("mute", "unmute", "mute audio", "toggle mute"): ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],

    #----------------- SHUTDOWN DAEMON -----------------------
    ("close assistant", "shutdown assistant", "turn off", "goodbye", "exit"): "FECHAR"
}

# Flattens the grouped commands dictionary for the fuzzy matching processor
COMANDOS_PERMITIDOS = {phrase: command for phrases, command in COMANDOS_AGRUPADOS.items() for phrase in phrases}

# English wake words
GATILHOS_LUCY = ["friday", "hey friday"]

def enviar_notificacao(titulo, message, urgency="low"):
    try:
        subprocess.Popen(["notify-send", "-a", "Friday English", "-u", urgency, titulo, message])
    except FileNotFoundError:
        pass

def processar_comando_fuzzy(fala_usuario):
    fala_usuario = fala_usuario.lower().strip()
    if not fala_usuario:
        return

    # 1. WAKE WORD REMOVAL FROM COMBINED STRINGS
    for gatilho in GATILHOS_LUCY:
        if fala_usuario.startswith(gatilho):
            fala_usuario = fala_usuario.replace(gatilho, "", 1).strip()

    if not fala_usuario:
        return

    print(f"-> Analyzing clean text: '{fala_usuario}'")
    
    melhor_comando = None
    maior_porcentagem = 0
    
    # 2. STRICT CHARACTER CORRESPONDENCE LOGIC
    for comando_esperado in COMANDOS_PERMITIDOS.keys():
        porcentagem = fuzz.token_sort_ratio(comando_esperado, fala_usuario)
        if porcentagem > maior_porcentagem:
            maior_porcentagem = porcentagem
            melhor_comando = comando_esperado
            
    print(f"   [Fuzzy Match] Highest certainty: {maior_porcentagem}% with '{melhor_comando}'")

    # 3. HIGH SECURITY THRESHOLD (80% minimum match required)
    if maior_porcentagem >= 80:
        if COMANDOS_PERMITIDOS[melhor_comando] == "FECHAR":
            enviar_notificacao("Friday", "Shutting down offline mode. See you later!", "normal")
            if os.path.exists("/tmp/friday_en.pid"):
                os.remove("/tmp/friday_en.pid")
            os._exit(0)
            
        subprocess.Popen(COMANDOS_PERMITIDOS[melhor_comando], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         start_new_session=True)
        enviar_notificacao("Success", f"Executing: {melhor_comando}")
    else:
        print(f"   [Blocked] Command ignored due to low confidence score.")
        enviar_notificacao("Friday", f"Did not understand: '{fala_usuario}'", "low")

# --- MAIN ENGINE LOOP ---
def iniciar_assistente():
    print("Loading offline English model (Vosk)...")
    model = Model(MODEL_PATH)
    
    # Active strict vocabulary filter for enhanced background noise cancellation
    lista_palavras = list(COMANDOS_PERMITIDOS.keys()) + GATILHOS_LUCY
    palavras_chave_json = json.dumps(lista_palavras)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE, palavras_chave_json)
    recognizer.SetWords(True)

    print("✨ Friday Offline (English) ready and listening!")
    enviar_notificacao("Friday Online", "English offline mode successfully initialized.")

    # Opens the raw audio stream from your default microhone channel
    with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=4000, dtype='int16',
                           channels=1, callback=audio_callback):
        
        modo_comando = False
        
        while True:
            data = audio_queue.get()
            
            if recognizer.AcceptWaveform(data):
                resultado = json.loads(recognizer.Result())
                texto = resultado.get("text", "")
                
                if modo_comando:
                    processar_comando_fuzzy(texto)
                    modo_comando = False
                else:
                    for gatilho in GATILHOS_LUCY:
                        if gatilho in texto:
                            enviar_notificacao("🎙️ Friday", "Listening... Say your command.", "normal")
                            modo_comando = True
                            
                            texto_restante = texto.split(gatilho, 1)[-1].strip()
                            if texto_restante:
                                processar_comando_fuzzy(texto_restante)
                                modo_comando = False
                            break

if __name__ == "__main__":
    # PID Lock Implementation to prevent hardware sounddevice overlap bugs
    pid_file = "/tmp/friday_en.pid"
    if os.path.exists(pid_file):
        print("Error: Friday English is already running in another instance!")
        sys.exit(1)
        
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        iniciar_assistente()
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)