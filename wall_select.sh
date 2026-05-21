#!/bin/bash
DIR="$HOME/Imagens/Wallpapers"

# Lista os ficheiros numerados e abre o rofi para escolheres
ESCOLHA=$(ls "$DIR" | rofi -dmenu -p "Selecionar Wallpaper:")

# Se escolheres algo (não cancelares), aplica
if [ -n "$ESCOLHA" ]; then
    awww img "$DIR/$ESCOLHA"
fi
