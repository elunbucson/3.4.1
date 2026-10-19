# Meta 3.4.1 · Navegación dinámica

Aplicación de escritorio para explorar rutas alternativas y comparar tres
políticas de recálculo ante bloqueos e incidentes simulados. La red vial está
basada en OpenStreetMap; los tiempos y eventos son una simulación académica,
no tráfico en tiempo real ni indicaciones para conducir.

## Configuración privada

Este repositorio no incluye coordenadas de origen ni trazos personales.
Antes de ejecutar el modelo:

1. Copia `config_local.example.py` con el nombre `config_local.py`.
2. En `config_local.py`, define `ORIGEN = (latitud, longitud)` para un punto
   que quieras usar en tu computadora.
3. Ejecuta `Ejecutar_modelo.bat`.

`config_local.py` está excluido de Git. Si no hay archivos GPX/KML locales,
la ventana genera y muestra tres alternativas a partir de la red vial. Para
usar trazos propios, colócalos en `rutas_habituales/`; esa carpeta también
está excluida del repositorio.

## Ejecución

En Windows, abre una terminal en esta carpeta y ejecuta:

```powershell
.\Ejecutar_modelo.bat
```

La aplicación usa Tkinter y no requiere extensiones de Visual Studio Code.
Python 3.10 o posterior es recomendado.

## Datos

- `datos/red_vial.json`: grafo dirigido simplificado derivado de OpenStreetMap.
- `datos/osm_corredores.json`: extracto vial de Geofabrik para la región de
  estudio, descargado el 18-10-2026. Datos ODbL 1.0; © OpenStreetMap
  contributors.

Las demoras, velocidades, cierres, retenes y zonas simuladas son parámetros
del modelo y no reflejan condiciones actuales de la vía.

