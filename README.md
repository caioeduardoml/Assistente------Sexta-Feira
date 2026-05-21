# 🎙️ Sexta-Feira: Assistente de Voz Offline para Hyprland

A **Sexta-Feira** é um assistente de voz leve, modular e **100% offline** desenvolvido especificamente para o ecossistema **Arch Linux + Hyprland**. Utilizando o motor de reconhecimento de fala **Vosk** e o algoritmo de busca aproximada **RapidFuzz**, o projeto permite controlar janelas, gerenciar mídias (Spotify), ajustar volumes e abrir aplicações de forma instantânea através de comandos de voz, com consumo mínimo de recursos de hardware.

---

## ✨ Funcionalidades Prontas para Uso

* **100% Offline & Privacidade Garantida:** Sem envio de dados para servidores externos (Google, Amazon ou OpenAI).
* **Controle de Janelas Nativo (Hyprland):** Fechamento de janelas por classe (`class`), alternância de tela cheia e encerramento forçado usando `hyprctl`.
* **Controle de Mídia Inteligente:** Comandos para abrir o Spotify Web encapsulado no Brave Browser como WebApp (`--app`), além de comandos para pausar, dar play e pular faixas via `playerctl`.
* **Gerenciamento de Áudio Universal:** Controle preciso do ganho de volume (aumentar, diminuir e alternar mudo) baseado na API do WirePlumber (`wpctl`).
* **Algoritmo Anti-Falso-Positivo:** Substituição do processamento parcial por correspondência estrita baseada em tokens (`fuzz.token_sort_ratio`) com limite seguro de 80%, evitando aberturas acidentais (ex: confundir Discord com VS Code).
* **Trava de Instância Única (PID Lock):** Mecanismo automático para impedir que múltiplos daemons tentem disputar o mesmo canal de captura de áudio.

---

## 🛠️ Pré-requisitos do Sistema

Antes de rodar o assistente, certifique-se de ter os pacotes de sistema necessários instalados no seu Arch Linux.

```bash
# Instalar dependências de áudio, controle de mídia e ferramentas auxiliares
sudo pacman -S python-pip sounddevice-dependencies playerctl wireplumber libnotify wget unzip
