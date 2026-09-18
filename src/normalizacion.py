"""Normalización y diagnóstico de los datos de entrada."""

from __future__ import annotations

import re
from typing import Any

import numpy as np
import pandas as pd


COLUMN_MAP = {
    "Consecutivo\nMaps": "id_obra",
    "Nombre del sujeto fiscalizado": "sujeto_fiscalizado",
    "Número de contrato": "numero_contrato",
    "Fecha de contrato": "fecha_contrato",
    "Nombre de la obra o servicio relacionado": "obra_servicio",
    "Nombre del contratista": "contratista",
    "Supervisión Externa": "supervision_externa",
    "Supervisor Interno": "supervisor_interno",
    "Cordinador Interno": "coordinador_interno",
    "Importe contratado /Importe Administración directa": "importe_contratado",
    "Latitud": "latitud",
    "Longitud": "longitud",
    "Auditor": "auditor",
    "Tiempo apróximado de revisión en la obra(Horas)": "duracion_horas",
    "Tipo de Inspección": "tipo_inspeccion",
}

MISSING_TEXT_VALUES = {
    "",
    "sin dato",
    "s/d",
    "n/a",
    "na",
    "ninguno",
    "none",
    "nan",
}


def _clean_text(value: Any) -> Any:
    """Limpia texto y convierte marcadores de ausencia a NA."""
    if pd.isna(value):
        return pd.NA

    value = str(value).strip()
    value = re.sub(r"\s+", " ", value)

    if value.lower() in MISSING_TEXT_VALUES:
        return pd.NA

    return value


def _parse_fecha(value: Any) -> pd.Timestamp:
    """Convierte fechas de Excel o texto sin generar advertencias de formato."""
    if pd.isna(value):
        return pd.NaT

    if isinstance(value, (pd.Timestamp, np.datetime64)):
        return pd.to_datetime(value, errors="coerce")

    clean = _clean_text(value)
    if pd.isna(clean):
        return pd.NaT

    return pd.to_datetime(
        clean,
        errors="coerce",
        format="mixed",
        dayfirst=True,
    )


def _parse_importe(value: Any) -> float:
    """Convierte importes a número; los valores no informados quedan como NaN."""
    if pd.isna(value):
        return np.nan

    text = str(value).strip()
    if text.lower() in MISSING_TEXT_VALUES:
        return np.nan

    text = (
        text.replace("$", "")
        .replace(",", "")
        .replace(" ", "")
    )

    try:
        return float(text)
    except ValueError:
        return np.nan


def normalizar_datos(df: pd.DataFrame) -> pd.DataFrame:
    """Genera una copia normalizada sin alterar el DataFrame original."""
    faltantes = [c for c in COLUMN_MAP if c not in df.columns]
    if faltantes:
        raise ValueError(
            "Faltan columnas esperadas en el archivo fuente: "
            + ", ".join(faltantes)
        )

    out = df.rename(columns=COLUMN_MAP).copy()

    text_columns = [
        "sujeto_fiscalizado",
        "numero_contrato",
        "obra_servicio",
        "contratista",
        "supervision_externa",
        "supervisor_interno",
        "coordinador_interno",
        "auditor",
        "tipo_inspeccion",
    ]

    for column in text_columns:
        out[column] = out[column].map(_clean_text)

    out["fecha_contrato"] = out["fecha_contrato"].map(_parse_fecha)

    out["importe_contratado"] = out["importe_contratado"].map(_parse_importe)

    for column in ["latitud", "longitud", "duracion_horas"]:
        out[column] = pd.to_numeric(out[column], errors="coerce")

    out["tipo_inspeccion"] = (
        out["tipo_inspeccion"]
        .astype("string")
        .str.strip()
        .str.title()
    )

    out["auditor"] = (
        out["auditor"]
        .astype("string")
        .str.strip()
        .str.upper()
    )

    return out


def diagnosticar_datos(df: pd.DataFrame) -> dict:
    """Devuelve indicadores útiles antes de construir el optimizador."""
    diagnostico = {
        "registros": int(len(df)),
        "columnas": int(len(df.columns)),
        "tipos_inspeccion": df["tipo_inspeccion"].value_counts(dropna=False).to_dict(),
        "auditores": df["auditor"].value_counts(dropna=False).to_dict(),
        "duraciones_horas": sorted(
            df["duracion_horas"].dropna().unique().tolist()
        ),
        "filas_sin_coordenadas": int(
            (df["latitud"].isna() | df["longitud"].isna()).sum()
        ),
        "filas_coordenadas_fuera_rango": int(
            (
                (~df["latitud"].between(-90, 90))
                | (~df["longitud"].between(-180, 180))
            ).fillna(False).sum()
        ),
        "filas_sin_duracion": int(df["duracion_horas"].isna().sum()),
        "filas_duracion_no_positiva": int(
            (df["duracion_horas"].fillna(0) <= 0).sum()
        ),
        "filas_sin_auditor": int(df["auditor"].isna().sum()),
        "filas_sin_importe": int(df["importe_contratado"].isna().sum()),
        "filas_sin_fecha_contrato": int(df["fecha_contrato"].isna().sum()),
    }

    return diagnostico


def tabla_calidad(df: pd.DataFrame) -> pd.DataFrame:
    """Construye una tabla simple de calidad por columna."""
    rows = []
    for column in df.columns:
        rows.append(
            {
                "columna": column,
                "tipo": str(df[column].dtype),
                "nulos": int(df[column].isna().sum()),
                "no_nulos": int(df[column].notna().sum()),
                "unicos": int(df[column].nunique(dropna=True)),
            }
        )
    return pd.DataFrame(rows)
