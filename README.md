# ProgInspecciones2

Prototipo controlado para la programación y optimización de inspecciones físicas.

## Fase 0

La primera etapa del proyecto valida únicamente la infraestructura técnica:

1. Ejecutar el proyecto desde Google Colab.
2. Montar Google Drive.
3. Leer el archivo Excel fuente desde una ruta fija.
4. Validar que la hoja esperada exista.
5. Mostrar un resumen básico de los datos cargados.

Todavía no se implementa el optimizador.

## Fuente de datos

El archivo Excel se mantendrá en Google Drive:

```text
MyDrive/Colab Notebooks/PROGRAMAS_2026/INSPECCION_FISICA/INSPECCION_1_MLEO_AIN.xlsx
```

Hoja inicial:

```text
Inspección física_OBP
```

## Estructura

```text
ProgInspecciones2/
├── README.md
├── requirements.txt
├── .gitignore
├── notebooks/
│   └── 00_prueba_conexion_colab.ipynb
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── paths.py
│   ├── carga_datos.py
│   └── validacion.py
├── data/
│   └── .gitkeep
└── results/
    └── .gitkeep
```

## Principio del proyecto

- **GitHub:** código fuente y control de versiones.
- **Google Drive:** archivo Excel de entrada.
- **Google Colab:** ejecución, pruebas y visualización.


## Notebook operativo

A partir de la Fase 2, el notebook de uso normal es:

```text
notebooks/ProgInspecciones2_COLAB.ipynb
```

Este notebook contiene una sola celda de ejecución. Cada vez que se ejecuta:

1. monta Google Drive;
2. clona o actualiza el repositorio con `git pull`;
3. instala las dependencias;
4. ejecuta `run_pipeline.py`.

Por lo tanto, los cambios futuros se realizan principalmente en los archivos del repositorio y no requieren editar manualmente el notebook.
