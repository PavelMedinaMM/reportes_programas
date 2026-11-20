# Reportes de desempeño de programas — Canal 6

Copia actualizada de los PDF que generan los reportes automáticos (fuente: HR Media). Una carpeta por programa:

| Carpeta | Programa | Frecuencia | Repo de origen |
|---|---|---|---|
| `Telediario_Matutino/` | Telediario Matutino | Diario L–V | TDM |
| `Telediario_Vespertino/` | Telediario Vespertino | Diario L–V | TDV |
| `Telediario_Nocturno/` | Telediario Nocturno | Diario L–V | TDN |
| `Vivalavi/` | Vivalavi | Diario L–V | VLV |
| `Cuando_los_Angeles_Caen/` | Cuando los Ángeles Caen | Diario L–V | CLAC |
| `C4_en_Alerta/` | C4 en Alerta | Diario L–V | C4 |
| `Rumbo_al_Campeonato/` | Rumbo al Campeonato | Semanal (domingos) | RAC |
| `Tocando_al_Corazon/` | Tocando al Corazón | Manual | TAC |

Los archivos se nombran `<Programa>_Desempeno_<AAAA-MM-DD>.pdf`, donde la fecha es el día de transmisión.
Las tareas programadas copian aquí los PDF después de cada corrida; no edites los archivos a mano.

Información confidencial de Multimedios. Dirección Data Analytics.

## Copia en Google Drive
Carpeta: https://drive.google.com/drive/folders/1qgFsuxKbj7mmx99L0nS-kKLXwDvHUQ1i (misma estructura).
Una tarea programada (L–V 11:45) sube a Drive los PDF nuevos o modificados. `drive_sync.json` guarda el estado
sincronizado (sha256 por archivo) y `python3 drive_plan.py` lista lo pendiente. Si una carpeta de programa es nueva,
créala en Drive y agrega su ID a `drive_folders`.
