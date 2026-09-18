"""Exportación y visualización de resultados del programador."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def exportar_programacion_csv(
    programacion: pd.DataFrame,
    ruta_excel_fuente: str,
    nombre_archivo: str = "PROGRAMACION_RESULTADO_V1.csv",
) -> Path:
    """Guarda la programación junto al Excel fuente en Google Drive."""
    carpeta = Path(ruta_excel_fuente).parent
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_salida = carpeta / nombre_archivo

    # utf-8-sig facilita la apertura directa en Excel con acentos correctos.
    programacion.to_csv(
        ruta_salida,
        index=False,
        encoding="utf-8-sig",
    )
    return ruta_salida


def grafica_actividades_por_dia(programacion: pd.DataFrame) -> None:
    """Muestra número de actividades por día y tipo."""
    tabla = (
        programacion
        .assign(tipo=programacion["tipo"].astype(str))
        .groupby(["dia", "tipo"])
        .size()
        .unstack(fill_value=0)
        .sort_index()
    )

    ax = tabla.plot(kind="bar", stacked=True, figsize=(10, 5))
    ax.set_title("Actividades programadas por día")
    ax.set_xlabel("Día")
    ax.set_ylabel("Número de actividades")
    ax.legend(title="Tipo")
    plt.xticks(rotation=0)
    plt.tight_layout()
    plt.show()


def grafica_carga_auditores(cargas: pd.DataFrame) -> None:
    """Muestra una matriz auditor x día con carga diaria en horas."""
    if cargas.empty:
        return

    matriz = (
        cargas
        .pivot_table(
            index="auditor",
            columns="dia",
            values="carga_horas",
            aggfunc="max",
            fill_value=0,
        )
        .sort_index()
    )

    fig, ax = plt.subplots(figsize=(10, max(5, len(matriz) * 0.45)))
    im = ax.imshow(matriz.values, aspect="auto")

    ax.set_title("Carga diaria por auditor (horas)")
    ax.set_xlabel("Día")
    ax.set_ylabel("Auditor")
    ax.set_xticks(range(len(matriz.columns)))
    ax.set_xticklabels([f"Día {d}" for d in matriz.columns])
    ax.set_yticks(range(len(matriz.index)))
    ax.set_yticklabels(matriz.index)

    for i in range(len(matriz.index)):
        for j in range(len(matriz.columns)):
            valor = float(matriz.iloc[i, j])
            ax.text(j, i, f"{valor:.1f}", ha="center", va="center")

    fig.colorbar(im, ax=ax, label="Horas")
    plt.tight_layout()
    plt.show()


def grafica_ubicaciones_por_dia(programacion: pd.DataFrame) -> None:
    """Muestra la distribución geográfica aproximada de actividades por día."""
    if programacion.empty:
        return

    fig, ax = plt.subplots(figsize=(9, 7))

    for dia, grupo in programacion.groupby("dia"):
        ax.scatter(
            grupo["longitud"],
            grupo["latitud"],
            label=f"Día {dia}",
            alpha=0.75,
        )

    ax.set_title("Ubicación de actividades por día")
    ax.set_xlabel("Longitud")
    ax.set_ylabel("Latitud")
    ax.legend(title="Programación", bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, alpha=0.25)
    plt.tight_layout()
    plt.show()


def mostrar_resumen_diario(
    programacion: pd.DataFrame,
    equipos: pd.DataFrame,
    cargas: pd.DataFrame,
) -> pd.DataFrame:
    """Construye un resumen compacto por día."""
    acts = (
        programacion.groupby("dia")
        .agg(
            actividades=("id_obra", "count"),
            horas_actividades=("duracion_horas", "sum"),
        )
    )

    fisicas = (
        programacion[
            programacion["tipo"].astype(str).str.lower().str.startswith("f")
        ]
        .groupby("dia")
        .size()
        .rename("fisicas")
    )

    proyectos = (
        programacion[
            programacion["tipo"].astype(str).str.lower().str.startswith("p")
        ]
        .groupby("dia")
        .size()
        .rename("proyectos")
    )

    parejas = (
        equipos.groupby("dia").size().rename("parejas")
        if not equipos.empty
        else pd.Series(dtype="int64", name="parejas")
    )

    carga_max = (
        cargas.groupby("dia")["carga_horas"].max().rename("carga_max_auditor")
        if not cargas.empty
        else pd.Series(dtype="float64", name="carga_max_auditor")
    )

    resumen = pd.concat(
        [acts, fisicas, proyectos, parejas, carga_max],
        axis=1,
    ).fillna(0)

    return resumen.reset_index()
