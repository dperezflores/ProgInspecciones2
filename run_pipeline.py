"""Punto de entrada único para ejecutar ProgInspecciones2 desde Colab."""

from __future__ import annotations

from pathlib import Path

from IPython.display import display

from src.carga_datos import cargar_hoja, listar_hojas, resumen_dataframe
from src.config import PROJECT_NAME, PROJECT_VERSION, SOURCE_SHEET
from src.normalizacion import diagnosticar_datos, normalizar_datos, tabla_calidad
from src.paths import SOURCE_EXCEL_PATH
from src.validacion import validar_dataframe_no_vacio


def ejecutar_diagnostico():
    """Carga, normaliza y diagnostica el archivo fuente."""
    print("=" * 70)
    print(f"{PROJECT_NAME} | versión {PROJECT_VERSION}")
    print("FASE ACTUAL: carga, normalización y diagnóstico")
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

    print("\nCALIDAD DE DATOS POR COLUMNA")
    display(tabla_calidad(df_norm))

    print("\nDATOS NORMALIZADOS — PRIMEROS 10 REGISTROS")
    display(df_norm.head(10))

    print("\n" + "=" * 70)
    print("EJECUCIÓN COMPLETADA CORRECTAMENTE")
    print("=" * 70)

    return df_norm


def main():
    ejecutar_diagnostico()


if __name__ == "__main__":
    main()
