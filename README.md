# Meta 3.4.1 - Navegación dinámica a UABC Campus Otay

El paquete reúne una **ventana de escritorio**, una notebook ejecutable y un
informe académico. Usa una red vial de OpenStreetMap guardada en `datos/` y
los tres trazos GPX/KML proporcionados por el alumno. La primera ejecución
no necesita descargar calles ni abrir un navegador.

## Abrir la ventana

En PowerShell, dentro de esta carpeta:

```powershell
.\Ejecutar_modelo.bat
```

También puedes hacer doble clic en el BAT. Abre una ventana nativa con los
tres trazos habituales, el recorrido elegido, bloqueos, retenes, tiempos
simulados, número de recálculos y nodos expandidos. Elige una política y
pulsa **Mostrar recorrido** o **Animar**. La ventana carga el mapa y ejecuta
las tres políticas al abrirse; puede tardar mientras calcula, pero debe
mostrar el estado de preparación.

El BAT prueba primero el Python incluido con Codex y después el Python
instalado en el equipo. Solo usa la biblioteca estándar para la ventana;
no exige una extensión de Visual Studio Code.

## Abrir y ejecutar la notebook

Archivo: `navegacion_uabc_dinamica.ipynb`. En un entorno Python 3.10 o
posterior, instala los paquetes una vez:

```powershell
python -m pip install -r notebook_requirements.txt
```

Ábrela en Jupyter o Visual Studio Code y selecciona el intérprete donde se
instalaron los paquetes. Ejecuta todas las celdas en orden. Incluye el código
del motor, auditoría topológica, comparación de las tres políticas, mapa y
gráfica. También hay una celda para exportar MP4 H.264 con Matplotlib/FFmpeg;
**permanece desactivada (`EXPORTAR_VIDEO = False`) por acuerdo con el alumno**.

## Datos y alcance

- `rutas_habituales/`: tres rutas aportadas en GPX/KML.
- `datos/osm_corredores.json`: extracto de carreteras y controles OSM
  recortado del archivo regional de México de Geofabrik del 18-10-2026;
  licencia ODbL 1.0, © OpenStreetMap contributors.
- `datos/red_vial.json`: grafo dirigido simplificado derivado del extracto.
- `resultados/experimento_341.json`: auditoría y comparación reproducible con
  semilla 341.
- `Informe_Meta_3.4.1_Navegacion_Dinamica.pdf`: reflexión y análisis
  solicitados por el profesor.

El origen aproximado es la **entrada de la privada**, no el domicilio.
Las cinco ubicaciones de semáforos/altos aportadas por el alumno se estimaron
a partir de capturas. En esta extracción no hay etiquetas OSM del mismo tipo
a 80 m de ninguna; son candidatos a completar el mapa, pero requieren GPS
para fijar la posición exacta. Las fases de luz,
demoras, velocidades por tipo de calle, zonas de congestión e incidentes son
parámetros de una simulación académica; no representan tráfico en tiempo real
ni instrucciones para conducir.

## Reproducibilidad

La ventana y la notebook usan el mismo motor `motor_dinamico.py` y la misma
semilla. La notebook contiene una copia visible del código para inspección.
El mapa se recortó del extracto regional después de que Overpass y la API
de bloques agotaran el tiempo de espera. La copia incluida evita nuevas
descargas al revisar la entrega.

