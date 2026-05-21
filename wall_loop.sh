#!/bin/bash
DIR="$HOME/Imagens/Wallpapers"

# Garante que o daemon está a correr
awww-daemon &
sleep 1

while true; do
    # O comando 'ls -v' ordena os arquivos de forma numérica natural (1, 2, 10 em vez de 1, 10, 2)
    for IMG in $(ls -v "$DIR"); do
        # Aplica a imagem atual
        awww img "$DIR/$IMG"
        
        # Espera 3 minutos (180 segundos) antes de passar para o próximo número
        sleep 180
    done
    # Quando terminar a lista (ex: chegou no 50.png), o loop 'while' reinicia do 1.png
done
