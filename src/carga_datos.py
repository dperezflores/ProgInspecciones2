"""Funciones para cargar el archivo fuente de inspecciones."""

from pathlib import Path
from typing import List

import pandas as pd


def verificar_archivo(ruta: str) -> Path:
    """Verifica que el archivo fuente exista y devuelve su Path."""
    archivo = Path(ruta)
    if not archivo.exists():
        raise FileNotFoundError(
            "No se encontró el archivo fuente en la ruta indicada:\n"
            f"{ruta}"
        )
    return archivo


def listar_hojas(ruta: str) -> List[str]:
    """Devuelve la lista de hojas disponibles en el Excel."""
    verificar_archivo(ruta)
    with pd.ExcelFile(ruta, engine="openpyxl") as libro:
        return libro.sheet_names


def cargar_hoja(ruta: str, hoja: str) -> pd.DataFrame:
    """Carga una hoja específica del archivo Excel."""
    verificar_archivo(ruta)

    hojas = listar_hojas(ruta)
    if hoja not in hojas:
        raise ValueError(
            f"No se encontró la hoja '{hoja}'. "
            f"Hojas disponibles: {hojas}"
        )

    return pd.read_excel(
        ruta,
        sheet_name=hoja,
        engine="openpyxl",
    )


def resumen_dataframe(df: pd.DataFrame) -> dict:
    """Genera un resumen mínimo para la prueba de conexión."""
    return {
        "filas": int(df.shape[0]),
        "columnas": int(df.shape[1]),
        "nombres_columnas": list(df.columns),
        "celdas_vacias": int(df.isna().sum().sum()),
    }
