"""Modelo V1 para programación básica de inspecciones.

La V1 trabaja con parejas diarias de auditores, responsable obligatorio,
jornada objetivo de 8 horas, excedente permitido con penalización y
proximidad geográfica mediante Haversine.

No considera tiempos de traslado ni vehículos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Dict, Iterable, List, Tuple

import pandas as pd
from ortools.sat.python import cp_model


@dataclass
class ResultadoProgramacion:
    estado: str
    dias_usados: int
    horas_extra_totales: float
    apoyos_sin_actividad_propia: int
    distancia_emparejamiento_km: float
    programacion: pd.DataFrame
    equipos: pd.DataFrame
    cargas: pd.DataFrame


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia geodésica aproximada entre dos coordenadas."""
    r = 6371.0088
    p1, p2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dlambda / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _normalizar_tipo(valor: str) -> str:
    return str(valor).strip().lower()


def _crear_solver(limite_segundos: int = 60) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = limite_segundos
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False
    return solver


def _resolver_lexicografico(
    model: cp_model.CpModel,
    objetivos: List[Tuple[str, cp_model.LinearExpr]],
    limite_segundos: int,
) -> Tuple[cp_model.CpSolver, Dict[str, int], str]:
    """Optimiza objetivos uno por uno, fijando cada óptimo antes del siguiente."""
    valores: Dict[str, int] = {}
    ultimo_solver = None
    estado_final = "UNKNOWN"

    for nombre, expresion in objetivos:
        model.Minimize(expresion)
        solver = _crear_solver(limite_segundos)
        status = solver.Solve(model)
        ultimo_solver = solver

        if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            return solver, valores, solver.StatusName(status)

        valor = int(round(solver.ObjectiveValue()))
        valores[nombre] = valor

        # Solo fijamos el valor cuando el solver logró demostrar optimalidad.
        # Para esta V1 el problema es suficientemente pequeño para esperarlo.
        if status == cp_model.OPTIMAL:
            model.Add(expresion == valor)
        else:
            # No se debe fingir que un valor FEASIBLE es óptimo.
            return solver, valores, "FEASIBLE"

        estado_final = solver.StatusName(status)

    return ultimo_solver, valores, estado_final



def _asignar_horarios(
    programacion: pd.DataFrame,
    equipos: pd.DataFrame,
    hora_inicio_dia: str = "10:00",
) -> pd.DataFrame:
    """Asigna horas de inicio y fin coherentes con la lógica V1.

    Reglas:
    - La jornada comienza a las 10:00.
    - Los proyectos se programan primero.
    - Si ambos miembros de una pareja tienen proyectos, se ejecutan en paralelo.
    - Las físicas de la pareja comienzan cuando termina la fase de proyectos
      y se ejecutan secuencialmente porque requieren a ambos auditores.
    - No se agregan tiempos de traslado en esta versión.
    """
    df = programacion.copy()
    df["hora_inicio"] = pd.NA
    df["hora_fin"] = pd.NA

    base = datetime.strptime(hora_inicio_dia, "%H:%M")

    for dia in sorted(df["dia"].unique()):
        dia_df = df[df["dia"] == dia]

        parejas_dia = []
        if not equipos.empty:
            equipos_dia = equipos[equipos["dia"] == dia]
            parejas_dia = [
                (str(r["auditor_1"]), str(r["auditor_2"]))
                for _, r in equipos_dia.iterrows()
            ]

        auditores_emparejados = set()

        for a, b in parejas_dia:
            auditores_emparejados.update([a, b])

            fin_proyectos = {}

            for auditor in [a, b]:
                cursor = base
                proyectos_idx = dia_df[
                    (dia_df["responsable"].astype(str) == auditor)
                    & (
                        dia_df["tipo"]
                        .astype(str)
                        .str.lower()
                        .str.startswith("p")
                    )
                ].sort_values(["id_obra"]).index.tolist()

                for idx in proyectos_idx:
                    duracion = float(df.at[idx, "duracion_horas"])
                    inicio = cursor
                    fin = inicio + timedelta(hours=duracion)
                    df.at[idx, "hora_inicio"] = inicio.strftime("%H:%M")
                    df.at[idx, "hora_fin"] = fin.strftime("%H:%M")
                    cursor = fin

                fin_proyectos[auditor] = cursor

            cursor_fisicas = max(fin_proyectos.get(a, base), fin_proyectos.get(b, base))

            fisicas_idx = dia_df[
                (
                    dia_df["responsable"].astype(str).isin([a, b])
                )
                & (
                    dia_df["tipo"]
                    .astype(str)
                    .str.lower()
                    .str.startswith("f")
                )
            ].sort_values(
                ["responsable", "id_obra"],
                kind="stable",
            ).index.tolist()

            for idx in fisicas_idx:
                duracion = float(df.at[idx, "duracion_horas"])
                inicio = cursor_fisicas
                fin = inicio + timedelta(hours=duracion)
                df.at[idx, "hora_inicio"] = inicio.strftime("%H:%M")
                df.at[idx, "hora_fin"] = fin.strftime("%H:%M")
                cursor_fisicas = fin

        # Auditores no emparejados: en V1 solo deberían tener proyectos.
        for auditor in sorted(
            set(dia_df["responsable"].astype(str)) - auditores_emparejados
        ):
            cursor = base
            idxs = dia_df[
                dia_df["responsable"].astype(str) == auditor
            ].sort_values(
                ["tipo", "id_obra"],
                kind="stable",
            ).index.tolist()

            for idx in idxs:
                if pd.notna(df.at[idx, "hora_inicio"]):
                    continue
                duracion = float(df.at[idx, "duracion_horas"])
                inicio = cursor
                fin = inicio + timedelta(hours=duracion)
                df.at[idx, "hora_inicio"] = inicio.strftime("%H:%M")
                df.at[idx, "hora_fin"] = fin.strftime("%H:%M")
                cursor = fin

    return df

def programar_v1(
    df: pd.DataFrame,
    max_dias: int = 10,
    jornada_objetivo_horas: float = 8.0,
    limite_segundos_por_etapa: int = 60,
) -> ResultadoProgramacion:
    """Construye la primera programación por parejas.

    Supuestos principales:
    - Proyecto: 1 auditor responsable.
    - Física: responsable + 1 acompañante.
    - El responsable del Excel es obligatorio.
    - Una pareja diaria puede atender varias físicas de cualquiera de sus miembros.
    - Proyectos de ambos miembros pueden ejecutarse en paralelo.
    - Si solo uno tiene proyecto, el compañero puede apoyarlo.
    - Todas las actividades Proyecto se consideran en la misma ubicación común.
    - No se consideran tiempos de traslado en esta versión.
    """

    if df.empty:
        raise ValueError("No hay actividades para programar.")

    required = {
        "id_obra",
        "numero_contrato",
        "obra_servicio",
        "auditor",
        "duracion_horas",
        "tipo_inspeccion",
        "latitud",
        "longitud",
    }
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(
            "Faltan columnas requeridas para programar: " + ", ".join(sorted(missing))
        )

    work = df.reset_index(drop=True).copy()
    auditors = sorted(work["auditor"].dropna().astype(str).unique().tolist())
    auditor_idx = {a: k for k, a in enumerate(auditors)}
    n_aud = len(auditors)
    n_acts = len(work)

    # Media hora como unidad entera para CP-SAT.
    scale = 2
    dur = [int(round(float(h) * scale)) for h in work["duracion_horas"]]
    jornada = int(round(jornada_objetivo_horas * scale))
    max_dur_total = sum(dur)

    owners = [auditor_idx[str(a)] for a in work["auditor"]]
    types = [_normalizar_tipo(t) for t in work["tipo_inspeccion"]]
    is_fisica = [t.startswith("f") for t in types]
    is_proyecto = [t.startswith("p") for t in types]

    if not all(f or p for f, p in zip(is_fisica, is_proyecto)):
        bad = work.loc[
            [
                not (f or p)
                for f, p in zip(is_fisica, is_proyecto)
            ],
            "tipo_inspeccion",
        ].tolist()
        raise ValueError(f"Se encontraron tipos de inspección no reconocidos: {bad}")

    activities_by_aud: Dict[int, List[int]] = {a: [] for a in range(n_aud)}
    projects_by_aud: Dict[int, List[int]] = {a: [] for a in range(n_aud)}
    physicals_by_aud: Dict[int, List[int]] = {a: [] for a in range(n_aud)}

    for i in range(n_acts):
        a = owners[i]
        activities_by_aud[a].append(i)
        if is_proyecto[i]:
            projects_by_aud[a].append(i)
        else:
            physicals_by_aud[a].append(i)

    pairs = [(a, b) for a in range(n_aud) for b in range(a + 1, n_aud)]
    pair_index = {p: k for k, p in enumerate(pairs)}
    pairs_of_aud: Dict[int, List[Tuple[int, int]]] = {a: [] for a in range(n_aud)}
    for a, b in pairs:
        pairs_of_aud[a].append((a, b))
        pairs_of_aud[b].append((a, b))

    model = cp_model.CpModel()

    # x[i,d] = actividad i programada en día d.
    x = {
        (i, d): model.NewBoolVar(f"x_{i}_{d}")
        for i in range(n_acts)
        for d in range(max_dias)
    }

    # Día utilizado. Se fuerzan días contiguos 1..N.
    used = {d: model.NewBoolVar(f"used_{d}") for d in range(max_dias)}

    for i in range(n_acts):
        model.Add(sum(x[i, d] for d in range(max_dias)) == 1)
        for d in range(max_dias):
            model.Add(x[i, d] <= used[d])

    for d in range(max_dias):
        model.Add(sum(x[i, d] for i in range(n_acts)) >= used[d])
    for d in range(max_dias - 1):
        model.Add(used[d] >= used[d + 1])

    # own[a,d] = el auditor a tiene al menos una actividad propia ese día.
    own = {}
    for a in range(n_aud):
        for d in range(max_dias):
            v = model.NewBoolVar(f"own_{a}_{d}")
            own[a, d] = v
            acts = activities_by_aud[a]
            if acts:
                model.Add(sum(x[i, d] for i in acts) >= v)
                for i in acts:
                    model.Add(v >= x[i, d])
            else:
                model.Add(v == 0)

    # Pareja diaria.
    y = {
        (a, b, d): model.NewBoolVar(f"pair_{a}_{b}_{d}")
        for a, b in pairs
        for d in range(max_dias)
    }

    paired = {}
    for a in range(n_aud):
        for d in range(max_dias):
            incident = [y[p[0], p[1], d] for p in pairs_of_aud[a]]
            v = model.NewBoolVar(f"paired_{a}_{d}")
            paired[a, d] = v
            model.Add(sum(incident) == v)

    # Cada física elige exactamente un acompañante, y dicho acompañante
    # debe ser la pareja diaria del responsable.
    support = {}
    for i in range(n_acts):
        if not is_fisica[i]:
            continue
        a = owners[i]
        for d in range(max_dias):
            candidates = []
            for b in range(n_aud):
                if b == a:
                    continue
                p = (min(a, b), max(a, b))
                s = model.NewBoolVar(f"sup_{i}_{b}_{d}")
                support[i, b, d] = s
                model.Add(s <= y[p[0], p[1], d])
                candidates.append(s)
            model.Add(sum(candidates) == x[i, d])

    # Una pareja existe únicamente si al menos una física la necesita ese día.
    for a, b in pairs:
        for d in range(max_dias):
            relevant = []
            for i in physicals_by_aud[a]:
                relevant.append(support[i, b, d])
            for i in physicals_by_aud[b]:
                relevant.append(support[i, a, d])
            if relevant:
                model.Add(y[a, b, d] <= sum(relevant))
            else:
                model.Add(y[a, b, d] == 0)

    # Cargas propias por tipo.
    project_load = {}
    physical_load = {}
    for a in range(n_aud):
        for d in range(max_dias):
            pvar = model.NewIntVar(0, max_dur_total, f"pload_{a}_{d}")
            fvar = model.NewIntVar(0, max_dur_total, f"fload_{a}_{d}")
            project_load[a, d] = pvar
            physical_load[a, d] = fvar
            model.Add(
                pvar
                == sum(dur[i] * x[i, d] for i in projects_by_aud[a])
            )
            model.Add(
                fvar
                == sum(dur[i] * x[i, d] for i in physicals_by_aud[a])
            )

    # Carga de una pareja:
    # max(proyectos de A, proyectos de B) + todas las físicas de ambos.
    pair_load = {}
    for a, b in pairs:
        for d in range(max_dias):
            pmax = model.NewIntVar(0, max_dur_total, f"pmax_{a}_{b}_{d}")
            model.AddMaxEquality(pmax, [project_load[a, d], project_load[b, d]])

            pload = model.NewIntVar(0, max_dur_total, f"pairload_{a}_{b}_{d}")
            pair_load[a, b, d] = pload
            model.Add(
                pload
                == pmax + physical_load[a, d] + physical_load[b, d]
            )

    # Carga ocupada por auditor.
    load = {}
    overtime = {}
    for a in range(n_aud):
        for d in range(max_dias):
            lvar = model.NewIntVar(0, max_dur_total, f"load_{a}_{d}")
            load[a, d] = lvar

            for p in pairs_of_aud[a]:
                model.Add(lvar == pair_load[p[0], p[1], d]).OnlyEnforceIf(
                    y[p[0], p[1], d]
                )

            model.Add(lvar == project_load[a, d]).OnlyEnforceIf(
                paired[a, d].Not()
            )

            ovar = model.NewIntVar(0, max_dur_total, f"overtime_{a}_{d}")
            overtime[a, d] = ovar
            model.Add(ovar >= lvar - jornada)

    # Uso de un auditor que no tiene actividad propia ese día.
    idle_partner = {}
    for a in range(n_aud):
        for d in range(max_dias):
            v = model.NewBoolVar(f"idlepartner_{a}_{d}")
            idle_partner[a, d] = v
            model.Add(v >= paired[a, d] - own[a, d])
            model.Add(v <= paired[a, d])
            model.Add(v <= 1 - own[a, d])

    # Distancia: para cada física y acompañante, si éste tiene actividades
    # propias ese día, se toma como referencia la más cercana.
    # Si no tiene actividad propia, la penalización se captura arriba.
    distance_terms = []
    for i in range(n_acts):
        if not is_fisica[i]:
            continue

        a = owners[i]
        lat_i = float(work.at[i, "latitud"])
        lon_i = float(work.at[i, "longitud"])

        for b in range(n_aud):
            if b == a:
                continue

            own_acts_b = activities_by_aud[b]
            if not own_acts_b:
                continue

            for d in range(max_dias):
                s = support[i, b, d]
                anchors = []

                for j in own_acts_b:
                    q = model.NewBoolVar(f"anchor_{i}_{b}_{j}_{d}")
                    model.Add(q <= s)
                    model.Add(q <= x[j, d])
                    anchors.append(q)

                    km = haversine_km(
                        lat_i,
                        lon_i,
                        float(work.at[j, "latitud"]),
                        float(work.at[j, "longitud"]),
                    )
                    # centésimas de km para conservar precisión con enteros.
                    distance_terms.append(int(round(km * 100)) * q)

                model.Add(sum(anchors) <= 1)
                model.Add(sum(anchors) >= s + own[b, d] - 1)

    total_overtime = sum(overtime.values())
    total_idle_partner = sum(idle_partner.values())
    total_days = sum(used.values())
    total_distance = sum(distance_terms) if distance_terms else 0

    objetivos = [
        ("overtime_units", total_overtime),
        ("idle_partner_days", total_idle_partner),
        ("days", total_days),
        ("distance_centi_km", total_distance),
    ]

    solver, valores, estado = _resolver_lexicografico(
        model,
        objetivos,
        limite_segundos_por_etapa,
    )

    if estado not in {"OPTIMAL", "FEASIBLE"}:
        raise RuntimeError(f"El modelo V1 no encontró solución. Estado: {estado}")

    # Reconstrucción de resultados.
    day_of = {}
    for i in range(n_acts):
        for d in range(max_dias):
            if solver.Value(x[i, d]):
                day_of[i] = d
                break

    partner_of = {}
    for a, b in pairs:
        for d in range(max_dias):
            if solver.Value(y[a, b, d]):
                partner_of[a, d] = b
                partner_of[b, d] = a

    support_of = {}
    for key, var in support.items():
        if solver.Value(var):
            i, b, d = key
            support_of[i] = b

    dias_usados = int(valores.get("days", sum(solver.Value(v) for v in used.values())))

    # Carga por auditor/día.
    cargas_rows = []
    for d in range(dias_usados):
        for a, name in enumerate(auditors):
            horas = solver.Value(load[a, d]) / scale
            if horas > 0 or solver.Value(paired[a, d]) or solver.Value(own[a, d]):
                b = partner_of.get((a, d))
                cargas_rows.append(
                    {
                        "dia": d + 1,
                        "auditor": name,
                        "pareja": auditors[b] if b is not None else None,
                        "actividad_propia": bool(solver.Value(own[a, d])),
                        "carga_horas": horas,
                        "excedente_horas": max(0.0, horas - jornada_objetivo_horas),
                    }
                )

    cargas_df = pd.DataFrame(cargas_rows)

    # Equipos diarios.
    equipos_rows = []
    for d in range(dias_usados):
        for a, b in pairs:
            if solver.Value(y[a, b, d]):
                horas = solver.Value(pair_load[a, b, d]) / scale
                equipos_rows.append(
                    {
                        "dia": d + 1,
                        "auditor_1": auditors[a],
                        "auditor_2": auditors[b],
                        "carga_equipo_horas": horas,
                        "auditor_1_con_actividad_propia": bool(solver.Value(own[a, d])),
                        "auditor_2_con_actividad_propia": bool(solver.Value(own[b, d])),
                    }
                )

    equipos_df = pd.DataFrame(equipos_rows)

    # Tabla de actividades.
    program_rows = []
    for i, row in work.iterrows():
        d = day_of[i]
        a = owners[i]
        b = support_of.get(i)

        program_rows.append(
            {
                "dia": d + 1,
                "id_obra": row["id_obra"],
                "contrato": row["numero_contrato"],
                "tipo": row["tipo_inspeccion"],
                "duracion_horas": float(row["duracion_horas"]),
                "responsable": auditors[a],
                "acompanante": auditors[b] if b is not None else None,
                "obra_servicio": row["obra_servicio"],
                "latitud": float(row["latitud"]),
                "longitud": float(row["longitud"]),
            }
        )

    program_df = (
        pd.DataFrame(program_rows)
        .sort_values(["dia", "tipo", "responsable", "id_obra"], kind="stable")
        .reset_index(drop=True)
    )

    program_df = _asignar_horarios(
        program_df,
        equipos_df,
        hora_inicio_dia="10:00",
    )

    columnas = [
        "dia",
        "hora_inicio",
        "hora_fin",
        "id_obra",
        "contrato",
        "tipo",
        "duracion_horas",
        "responsable",
        "acompanante",
        "obra_servicio",
        "latitud",
        "longitud",
    ]
    program_df = (
        program_df[columnas]
        .sort_values(
            ["dia", "hora_inicio", "responsable", "id_obra"],
            kind="stable",
        )
        .reset_index(drop=True)
    )

    horas_extra = solver.Value(total_overtime) / scale
    apoyos_sin_propia = solver.Value(total_idle_partner)
    distancia_km = (
        solver.Value(total_distance) / 100
        if not isinstance(total_distance, int)
        else float(total_distance) / 100
    )

    return ResultadoProgramacion(
        estado=estado,
        dias_usados=dias_usados,
        horas_extra_totales=horas_extra,
        apoyos_sin_actividad_propia=apoyos_sin_propia,
        distancia_emparejamiento_km=distancia_km,
        programacion=program_df,
        equipos=equipos_df,
        cargas=cargas_df,
    )
