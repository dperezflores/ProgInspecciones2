"""Validaciones iniciales del archivo fuente."""

import pandas as pd


def validar_dataframe_no_vacio(df: pd.DataFrame) -> None:
    """Valida que la hoja tenga filas y columnas."""
    if df.empty:
        raise ValueError("La hoja cargada no contiene registros.")

    if len(df.columns) == 0:
        raise ValueError("La hoja cargada no contiene columnas.")


def validar_columnas(df: pd.DataFrame, columnas_requeridas: list[str]) -> list[str]:
    """Devuelve las columnas requeridas que no existen en el DataFrame."""
    return [
        columna
        for columna in columnas_requeridas
        if columna not in df.columns
    ]
