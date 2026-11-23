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
| `Tocando_al_Corazon/` | Tocando al Corazón | Diario L–V | TAC |
| `Consolidado/` | Todos los programas en un PDF con índice | Diario L–V | este repo (`build_consolidado.py`) |

Los archivos se nombran `<Programa>_Desempeno_<AAAA-MM-DD>.pdf`, donde la fecha es el día de transmisión.
Las tareas programadas copian aquí los PDF después de cada corrida; no edites los archivos a mano.

Información confidencial de Multimedios. Dirección Data Analytics.

## Reporte consolidado
`Consolidado/Consolidado_Programas_<AAAA-MM-DD>.pdf`: un PDF por día hábil con portada, índice clicable
(share de franja y lugar por plaza), marcadores y enlace de regreso al índice en el encabezado de cada página.
Enlace "Clic aquí" a la carpeta de Drive con los reportes individuales en la portada, el índice y el pie de cada página
(`DRIVE_URL` en `build_consolidado.py`).
- Programas diarios: entran solo si tienen reporte de ese mismo día; si no, se omiten (el índice los lista como no incluidos).
- Programas de fin de semana (Rumbo al Campeonato): entra su emisión del fin de semana inmediato anterior; si no existe, se omite.
- La fecha del nombre, la portada ("Datos al") y los encabezados es la del último dato incluido; ningún consolidado trae datos posteriores a esa fecha. El índice muestra la fecha de cada programa.
- `python3 build_consolidado.py --elaborado <HOY>` revisa todos los días desde el 1 nov 2026 y solo regenera los que
  cambiaron (`Consolidado/manifest.json` guarda el sha256 de los reportes de entrada). Lo corre una tarea programada L–V 11:40.

## Copia en Google Drive
Carpeta: https://drive.google.com/drive/folders/1qgFsuxKbj7mmx99L0nS-kKLXwDvHUQ1i (misma estructura).
Una tarea programada (L–V 11:45) sube a Drive los PDF nuevos o modificados. `drive_sync.json` guarda el estado
sincronizado (sha256 por archivo) y `python3 drive_plan.py` lista lo pendiente. Si una carpeta de programa es nueva,
créala en Drive y agrega su ID a `drive_folders`.
