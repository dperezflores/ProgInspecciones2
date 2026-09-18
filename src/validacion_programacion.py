"""Validaciones posteriores del resultado del programador."""

from __future__ import annotations

import pandas as pd


def validar_resultado_v1(
    fuente: pd.DataFrame,
    programacion: pd.DataFrame,
    equipos: pd.DataFrame,
) -> dict:
    """Comprueba invariantes básicas de la programación V1."""
    errores = []

    if len(programacion) != len(fuente):
        errores.append(
            f"Se esperaban {len(fuente)} actividades y se obtuvieron "
            f"{len(programacion)}."
        )

    if programacion["id_obra"].duplicated().any():
        duplicados = programacion.loc[
            programacion["id_obra"].duplicated(keep=False), "id_obra"
        ].tolist()
        errores.append(f"Hay actividades duplicadas por id_obra: {duplicados}")

    responsables_fuente = (
        fuente[["id_obra", "auditor"]]
        .drop_duplicates(subset=["id_obra"])
        .set_index("id_obra")["auditor"]
        .astype(str)
        .to_dict()
    )

    for _, row in programacion.iterrows():
        esperado = responsables_fuente.get(row["id_obra"])
        if str(row["responsable"]) != str(esperado):
            errores.append(
                f"Responsable alterado en id_obra={row['id_obra']}: "
                f"esperado {esperado}, obtenido {row['responsable']}."
            )

        tipo = str(row["tipo"]).strip().lower()
        if tipo.startswith("f"):
            if pd.isna(row["acompanante"]):
                errores.append(
                    f"Inspección física sin acompañante: id_obra={row['id_obra']}."
                )
            elif str(row["acompanante"]) == str(row["responsable"]):
                errores.append(
                    f"Responsable y acompañante son iguales: id_obra={row['id_obra']}."
                )

    if not equipos.empty:
        miembros = []
        for _, row in equipos.iterrows():
            miembros.append((row["dia"], row["auditor_1"]))
            miembros.append((row["dia"], row["auditor_2"]))

        miembros_df = pd.DataFrame(miembros, columns=["dia", "auditor"])
        repetidos = miembros_df.duplicated(["dia", "auditor"], keep=False)
        if repetidos.any():
            casos = (
                miembros_df.loc[repetidos]
                .drop_duplicates()
                .to_dict("records")
            )
            errores.append(
                "Hay auditores asignados a más de una pareja el mismo día: "
                f"{casos}"
            )

        pair_lookup = set()
        for _, row in equipos.iterrows():
            pair_lookup.add(
                (
                    int(row["dia"]),
                    frozenset([str(row["auditor_1"]), str(row["auditor_2"])]),
                )
            )

        fisicas = programacion[
            programacion["tipo"].astype(str).str.lower().str.startswith("f")
        ]
        for _, row in fisicas.iterrows():
            key = (
                int(row["dia"]),
                frozenset([str(row["responsable"]), str(row["acompanante"])]),
            )
            if key not in pair_lookup:
                errores.append(
                    "La pareja de una física no aparece en la tabla de equipos: "
                    f"id_obra={row['id_obra']}."
                )

    return {
        "valido": not errores,
        "errores": errores,
        "actividades_programadas": int(len(programacion)),
        "fisicas_con_acompanante": int(
            (
                programacion["tipo"].astype(str).str.lower().str.startswith("f")
                & programacion["acompanante"].notna()
            ).sum()
        ),
    }
