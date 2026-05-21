#!/usr/bin/env python3
import os
import sys
import json
import queue
import subprocess
import sounddevice as sd
from vosk import Model, KaldiRecognizer
from rapidfuzz import fuzz

# --- CONFIGURAÇÃO DO MODELO E ÁUDIO ---
MODEL_PATH = os.path.expanduser("~/.config/hypr/scripts/model")
SAMPLE_RATE = 16000  # Taxa padrão recomendada pelo Vosk

if not os.path.exists(MODEL_PATH):
    print(f"Erro: Modelo não encontrado em {MODEL_PATH}. Baixe-o primeiro!")
    sys.exit(1)

# Fila para transferir o áudio da thread de captura para a thread de processamento
audio_queue = queue.Queue()

def audio_callback(indata, frames, time, status):
    """Esta função é chamada para cada bloco de áudio do microfone"""
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

# --- AUTOMAÇÃO E COMANDOS ---
# Ajustado com correções fonéticas (como o Vosk em PT-BR escuta palavras em inglês)
COMANDOS_AGRUPADOS = {
    #--------- ABRIR -------------------------------
    ("abrir vscode", "abrir vscode"): ["code", "--new-window"],
    ("abrir firefox", "abrir faiarfox", "abrir raposa"): ["firefox"],
    ("abrir discord canary", "abrir discordi canari", "abrir chat", "abrir chati"): ["discord-canary"],
    ("abrir gimp", "abrir gimpi", "abrir editor de imagem"): ["gimp"],
    ("abrir brave", "abrir breive", "abrir breve", "abrir brêivi"): ["brave"],
    ("abrir terminal", "abrir o terminal", "abrir kitty"): ["kitty"],

    #------------------ FECHAMENTO ------------------------------
    ("fechar vscode", "fechar vscode"): ["hyprctl", "dispatch", "closewindow", "class:^(code)$"],
    ("fechar firefox", "fechar faiarfox", "fechar raposa"): ["hyprctl", "dispatch", "closewindow", "class:^(firefox)$"],
    ("fechar discord canary", "fechar discordi canari", "fechar chat", "fechar chati"): ["hyprctl", "dispatch", "closewindow", "class:^(discord-canary)$"],
    ("fechar gimp", "fechar gimpi", "fechar editor de imagem"): ["hyprctl", "dispatch", "closewindow", "class:^(gimp)$"],
    ("fechar brave", "fechar breive", "fechar breve"): ["hyprctl", "dispatch", "closewindow", "class:^(brave-browser)$"],
    ("fechar terminal", "fechar kitty"): ["hyprctl", "dispatch", "closewindow", "class:^(kitty)$"],
    ("fechar janela", "fechar programa", "matar processo"): ["hyprctl", "dispatch", "killactive"],
    ("tela cheia", "maximizar", "janela inteira"): ["hyprctl", "dispatch", "fullscreen", "0"],
    
    # Música (Brave + Spotify Web)
    ("tocar musica", "colocar uma musica", "abrir spotify", "tocar esbofitai"): ["sh", "-c", "brave --app=https://open.spotify.com & sleep 3 && playerctl play"],
    ("pausar musica", "parar musica", "pause", "pausa"): ["playerctl", "pause"],
    ("continuar musica", "play na musica", "play", "lei musica", "lei", "plei"): ["playerctl", "play"],
    ("proxima musica", "pular musica", "proxima", "pular", "passar musica"): ["playerctl", "next"],

    # --- COMANDOS DE VOLUME (WIREPLUMBER / PIPEWIRE) ---
    ("aumentar volume", "aumentar o som", "mais alto", "subir volume"): ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%+"],
    ("diminuir volume", "diminuir o som", "mais baixo", "abaixar volume"): ["wpctl", "set-volume", "@DEFAULT_AUDIO_SINK@", "10%-"],
    ("mutar", "mutar o som", "tirar o som", "desmutar", "mudo"): ["wpctl", "set-mute", "@DEFAULT_AUDIO_SINK@", "toggle"],

    #----------------- FECHAR ASSISTENTE -----------------------
    ("fechar assistente", "desligar assistente", "desligar", "tchau", "encerrar"): "FECHAR"
}

# Desmembra o grupo acima para gerar o dicionário plano que o interpretador usa
COMANDOS_PERMITIDOS = {frase: comando for frases, comando in COMANDOS_AGRUPADOS.items() for frase in frases}

GATILHOS_LUCY = ["sexta-feira", "sexta feira"]

def enviar_notificacao(titulo, message, urgencia="low"):
    try:
        subprocess.Popen(["notify-send", "-a", "Sexta-Feira Vosk", "-u", urgencia, titulo, message])
    except FileNotFoundError:
        pass

def processar_comando_fuzzy(fala_usuario):
    fala_usuario = fala_usuario.lower().strip()
    if not fala_usuario:
        return

    # 1. LIMPEZA DE GATILHOS REMANESCENTES
    # Se o Vosk capturar "sexta feira abrir terminal" de uma vez só,
    # limpamos o gatilho para a comparação focar estritamente na ordem.
    for gatilho in GATILHOS_LUCY:
        if fala_usuario.startswith(gatilho):
            fala_usuario = fala_usuario.replace(gatilho, "", 1).strip()

    if not fala_usuario:
        return

    print(f"-> Analisando texto limpo: '{fala_usuario}'")
    
    melhor_comando = None
    maior_porcentagem = 0
    
    # 2. NOVA LÓGICA DE COMPARAÇÃO (MUITO MAIS ESTRITA)
    for comando_esperado in COMANDOS_PERMITIDOS.keys():
        # O token_sort_ratio ignora a ordem das palavras (ex: "volume aumentar" e "aumentar volume" dão 100%)
        # Mas exige que as palavras sejam correspondentes quase exatas, matando o bug do "discord/vscode"
        porcentagem = fuzz.token_sort_ratio(comando_esperado, fala_usuario)
        
        if porcentagem > maior_porcentagem:
            maior_porcentagem = porcentagem
            melhor_comando = comando_esperado
            
    print(f"   [Fuzzy Match] Maior certeza: {maior_porcentagem}% com '{melhor_comando}'")

    # 3. VALIDAÇÃO COM LIMITE ELEVADO (80% de precisão mínima)
    if maior_porcentagem >= 80:
        if COMANDOS_PERMITIDOS[melhor_comando] == "FECHAR":
            enviar_notificacao("Sexta-Feira", "Desligando modo offline. Até mais!", "normal")
            if os.path.exists("/tmp/sexta_feira.pid"):
                os.remove("/tmp/sexta_feira.pid")
            os._exit(0)
            
        subprocess.Popen(COMANDOS_PERMITIDOS[melhor_comando], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         start_new_session=True)
        enviar_notificacao("Sucesso", f"Executando: {melhor_comando}")
    else:
        # Se não atingiu 80%, ela ignora silenciosamente para não abrir apps errados no seu Hyprland
        print(f"   [Bloqueado] Comando ignorado por falta de certeza de segurança.")
        enviar_notificacao("Sexta-Feira", f"Não entendi: '{fala_usuario}'", "low")
        enviar_notificacao("Sexta-Feira", f"Ouvido: '{fala_usuario}' (Não reconhecido)")

# --- LOOP PRINCIPAL ---
def iniciar_assistente():
    print("Carregando modelo offline (Vosk)...")
    model = Model(MODEL_PATH)
    
    # ATIVADO: Filtro restrito de palavras passadas para o Kaldi
    # Garante precisão absurda ignorando ruídos externos!
    lista_palavras = list(COMANDOS_PERMITIDOS.keys()) + GATILHOS_LUCY
    palavras_chave_json = json.dumps(lista_palavras)
    recognizer = KaldiRecognizer(model, SAMPLE_RATE, palavras_chave_json)
    recognizer.SetWords(True)

    print("✨ Sexta-Feira Offline pronta e escutando!")
    enviar_notificacao("Sexta-Feira Online", "Modo offline inicializado com sucesso.")

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
                            enviar_notificacao("🎙️ Sexta-Feira", "Estou ouvindo... Diga o comando.", "normal")
                            modo_comando = True
                            
                            texto_restante = texto.split(gatilho, 1)[-1].strip()
                            if texto_restante:
                                processar_comando_fuzzy(texto_restante)
                                modo_comando = False
                            break

if __name__ == "__main__":
    # GARGALO CORRIGIDO: Sistema de Trava (PID Lock) para evitar múltiplas instâncias em background
    pid_file = "/tmp/sexta_feira.pid"
    if os.path.exists(pid_file):
        print("Erro: A Sexta-Feira já está rodando em outra instância!")
        sys.exit(1)
        
    with open(pid_file, "w") as f:
        f.write(str(os.getpid()))

    try:
        iniciar_assistente()
    except KeyboardInterrupt:
        print("\nEncerrando...")
    finally:
        if os.path.exists(pid_file):
            os.remove(pid_file)