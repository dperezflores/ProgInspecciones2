"""Punto de entrada único para ejecutar ProgInspecciones2 desde Colab."""

from __future__ import annotations

from pathlib import Path

from IPython.display import display

from src.carga_datos import cargar_hoja, listar_hojas, resumen_dataframe
from src.config import (
    JORNADA_OBJETIVO_HORAS,
    MAX_DIAS_V1,
    PROJECT_NAME,
    PROJECT_VERSION,
    SOLVER_TIME_LIMIT_SECONDS,
    SOURCE_SHEET,
)
from src.modelo_v1 import programar_v1
from src.normalizacion import diagnosticar_datos, normalizar_datos, tabla_calidad
from src.paths import SOURCE_EXCEL_PATH
from src.salidas import (
    exportar_programacion_csv,
    grafica_actividades_por_dia,
    grafica_carga_auditores,
    grafica_ubicaciones_por_dia,
    mostrar_resumen_diario,
)
from src.validacion import validar_dataframe_no_vacio
from src.validacion_programacion import validar_resultado_v1


def ejecutar_diagnostico():
    """Carga, normaliza y diagnostica el archivo fuente."""
    print("=" * 70)
    print(f"{PROJECT_NAME} | versión {PROJECT_VERSION}")
    print("FASE 1: carga, normalización y diagnóstico")
    print("=" * 70)

    ruta = Path(SOURCE_EXCEL_PATH)
    print(f"\nArchivo fuente:\n{ruta}")

    hojas = listar_hojas(SOURCE_EXCEL_PATH)
    print("\nHojas disponibles:")
    for hoja in hojas:
        print(f"  - {hoja}")

    df = cargar_hoja(SOURCE_EXCEL_PATH, SOURCE_SHEET)
    validar_dataframe_no_vacio(df)

    resumen = resumen_dataframe(df)
    print("\nRESUMEN DE CARGA")
    print("-" * 50)
    print(f"Registros: {resumen['filas']}")
    print(f"Columnas: {resumen['columnas']}")
    print(f"Celdas vacías: {resumen['celdas_vacias']}")

    df_norm = normalizar_datos(df)
    diagnostico = diagnosticar_datos(df_norm)

    print("\nDIAGNÓSTICO GENERAL")
    print("-" * 50)
    for clave, valor in diagnostico.items():
        if clave not in {"tipos_inspeccion", "auditores"}:
            print(f"{clave}: {valor}")

    print("\nTipos de inspección:")
    for tipo, cantidad in diagnostico["tipos_inspeccion"].items():
        print(f"  {tipo}: {cantidad}")

    print("\nAuditores:")
    for auditor, cantidad in diagnostico["auditores"].items():
        print(f"  {auditor}: {cantidad}")

    return df_norm


def ejecutar_programacion(df_norm):
    """Ejecuta y muestra el modelo V1."""
    print("\n" + "=" * 70)
    print("FASE 2 — PROGRAMADOR V1 POR PAREJAS")
    print("=" * 70)
    print("Supuestos de esta versión:")
    print("  • Jornada objetivo: 8 h; excedente permitido y penalizado.")
    print("  • Física: responsable + 1 acompañante.")
    print("  • Proyecto: responsable obligatorio.")
    print("  • Parejas diarias coherentes.")
    print("  • Cercanía por Haversine.")
    print("  • Proyecto antes de Física dentro de la lógica diaria.")
    print("  • Sin tiempos de traslado ni vehículos todavía.\n")

    resultado = programar_v1(
        df_norm,
        max_dias=MAX_DIAS_V1,
        jornada_objetivo_horas=JORNADA_OBJETIVO_HORAS,
        limite_segundos_por_etapa=SOLVER_TIME_LIMIT_SECONDS,
    )

    print("RESULTADO DEL MODELO")
    print("-" * 50)
    print(f"Estado: {resultado.estado}")
    print(f"Días utilizados: {resultado.dias_usados}")
    print(f"Horas extra totales: {resultado.horas_extra_totales:.1f}")
    print(
        "Auditor-día usado solo como apoyo: "
        f"{resultado.apoyos_sin_actividad_propia}"
    )
    print(
        "Distancia de emparejamiento acumulada: "
        f"{resultado.distancia_emparejamiento_km:.2f} km"
    )

    print("\nEQUIPOS POR DÍA")
    display(resultado.equipos)

    print("\nCARGA POR AUDITOR Y DÍA")
    display(resultado.cargas)

    print("\nRESUMEN DIARIO")
    resumen_diario = mostrar_resumen_diario(
        resultado.programacion,
        resultado.equipos,
        resultado.cargas,
    )
    display(resumen_diario)

    print("\nPROGRAMACIÓN DE ACTIVIDADES")
    display(resultado.programacion)

    ruta_csv = exportar_programacion_csv(
        resultado.programacion,
        SOURCE_EXCEL_PATH,
    )
    print("\nCSV GENERADO")
    print("-" * 50)
    print(ruta_csv)

    print("\nVISUALIZACIONES")
    grafica_actividades_por_dia(resultado.programacion)
    grafica_carga_auditores(resultado.cargas)
    grafica_ubicaciones_por_dia(resultado.programacion)

    validacion = validar_resultado_v1(
        df_norm,
        resultado.programacion,
        resultado.equipos,
    )

    print("\nVALIDACIÓN AUTOMÁTICA")
    print("-" * 50)
    if validacion["valido"]:
        print("✓ Programación estructuralmente válida.")
        print(
            f"✓ Actividades programadas: "
            f"{validacion['actividades_programadas']}"
        )
        print(
            f"✓ Físicas con acompañante: "
            f"{validacion['fisicas_con_acompanante']}"
        )
    else:
        print("✗ Se detectaron inconsistencias:")
        for error in validacion["errores"]:
            print(f"  - {error}")
        raise RuntimeError(
            "La solución del solver no superó la validación automática."
        )

    return resultado


def main():
    df_norm = ejecutar_diagnostico()
    ejecutar_programacion(df_norm)

    print("\n" + "=" * 70)
    print("EJECUCIÓN COMPLETADA")
    print("=" * 70)


if __name__ == "__main__":
    main()
