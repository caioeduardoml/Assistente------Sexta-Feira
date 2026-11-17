# Lucy (Sexta-Feira / Friday): Assistente Virtual Offline para Hyprland

A **Lucy** (originalmente **Sexta-Feira**) e uma assistente virtual leve, modular e **100% offline** desenvolvida para o ecossistema **Arch Linux + Hyprland**. Utilizando **Vosk** para reconhecimento de fala, **RapidFuzz** para busca aproximada anti-falso-positivo e **PySide6** para uma interface grafica com rosto animado, o projeto permite controlar janelas, gerenciar midias (Spotify/Playerctl), ajustar volumes (WirePlumber) e abrir aplicacoes por voz ou texto.

---

## Funcionalidades

- **Interface Grafica com Rosto Animado (Lucy):** Rosto holografico em 60 FPS com olhos que piscam naturalmente e acompanham o cursor, aneis HUD rotativos, expressoes por estado (aguardando, ouvindo, processando, falando, erro) e boca/equalizador reativos ao audio.
- **Modo Texto Integrado:** Permite enviar comandos digitados diretamente pela interface mesmo se o microfone ou modelo Vosk nao estiver disponivel.
- **Bilingue (PT-BR / EN-US):** Alternancia de idioma em tempo real na interface ou via parametro `--lang pt` / `--lang en`.
- **100% Offline e Privado:** Nenhum audio ou comando e enviado para servidores externos.
- **Controle de Janelas Nativo (Hyprland):** Fechamento por classe (`class`), encerramento ativo e tela cheia via `hyprctl`.
- **Controle de Midia e Audio:** Integracao com `playerctl` (Spotify/mplayer) e `wpctl` (WirePlumber/PipeWire).
- **Trava de Instancia Unica Inteligente (PID Lock):** Verifica se o PID salvo realmente esta ativo, removendo travas obsoletas automaticamente.

---

## Pre-requisitos e Instalacao

```bash
# Pacotes de sistema (Arch Linux)
sudo pacman -S python-pip portaudio playerctl wireplumber libnotify wget unzip

# Dependencias Python
pip install -r requirements.txt
```

---

## Como Executar

```bash
# Iniciar com interface grafica da Lucy (padrao PT-BR)
python3 lucy.py

# Iniciar em ingles
python3 lucy.py --lang en

# Especificar caminho customizado do modelo Vosk
python3 lucy.py --model /caminho/para/modelo

# Iniciar apenas em modo terminal/daemon (sem janela)
python3 lucy.py --no-gui
```

Os atalhos `sexta-feira.py` (padrao `pt`) e `friday.py` (padrao `en`) continuam funcionando normalmente.
