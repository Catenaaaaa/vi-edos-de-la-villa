#!/bin/bash
# Arma el video de presentación de Viñedos de la Villa (con Cate).
# Requisitos: voz/s1..s8.wav generados con Piper (ver voz/in.jsonl), capturas en img/ (capturas.py).
set -e
cd "$(dirname "$0")"
echo "== tiempos, subtítulos, música y efectos"
python3 prep.py
echo "== render (cuadro por cuadro)"
~/.venvs/playwright/bin/python -I render.py video
echo "== mezcla de audio"
ffmpeg -v error -y -i voz.wav -i musica.wav -i fx.wav -filter_complex "\
[0]aresample=48000,highpass=f=80,equalizer=f=3000:t=q:w=1:g=2,acompressor=threshold=-20dB:ratio=3:attack=5:release=80:makeup=3dB,asplit=2[v][vsc];\
[1]aresample=48000,volume=0.42[m];\
[m][vsc]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=350[md];\
[2]aresample=48000,volume=0.35[fx];\
[v][md][fx]amix=inputs=3:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11,aformat=channel_layouts=stereo[out]" -map "[out]" -c:a pcm_s16le mezcla.wav
echo "== final"
ffmpeg -v error -y -i video.mp4 -i mezcla.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest -movflags +faststart vinedos-de-la-villa-presentacion.mp4
ffprobe -v error -show_entries format=duration -of csv=p=0 vinedos-de-la-villa-presentacion.mp4
echo TERMINADO
