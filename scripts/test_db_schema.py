"""
EcoRuta — Verificación del esquema geoespacial.

Se conecta a la base PostgreSQL/PostGIS/pgRouting y comprueba:
  1. Que las extensiones `postgis` y `pgrouting` estén activas.
  2. Que existan todas las tablas del esquema base.
  3. Que las semillas de vehículos se hayan cargado correctamente.
  4. Que las columnas geométricas tengan índice espacial GiST.

Uso:
    python scripts/test_db_schema.py
    DATABASE_URL_SYNC=postgresql+psycopg2://... python scripts/test_db_schema.py

Devuelve código de salida 0 si todo es correcto, 1 en caso contrario.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

DEFAULT_DB_URL = "postgresql+psycopg2://ecoruta_user:ecoruta_secure_password@localhost:5432/ecoruta_db"

REQUIRED_EXTENSIONS: tuple[str, ...] = ("postgis", "pgrouting", "hstore")
REQUIRED_TABLES: tuple[str, ...] = (
    "vehicle_profiles",
    "road_nodes",
    "road_edges",
    "edge_hourly_speeds",
    "fuel_stations_cne",
    "hazard_zones",
    "data_ingest_audit",
)
REQUIRED_GIST_INDEXED: tuple[str, ...] = ("road_nodes", "road_edges", "fuel_stations_cne", "hazard_zones")


@dataclass
class CheckReport:
    ok: bool = True
    passed: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def record(self, condition: bool, message: str) -> None:
        if condition:
            self.passed.append(message)
        else:
            self.failed.append(message)
            self.ok = False

    def print_summary(self) -> None:
        print("\n" + "=" * 70)
        for msg in self.passed:
            print(f"  [OK]   {msg}")
        for msg in self.failed:
            print(f"  [FAIL] {msg}")
        print("=" * 70)
        print(f"Resultado: {'TODO CORRECTO' if self.ok else 'SE ENCONTRARON FALLOS'}")
        print(f"  Comprobaciones superadas: {len(self.passed)}")
        print(f"  Comprobaciones fallidas:  {len(self.failed)}")
        print("=" * 70 + "\n")


def build_engine() -> Engine:
    url = os.getenv("DATABASE_URL_SYNC", DEFAULT_DB_URL)
    return create_engine(url, pool_pre_ping=True, future=True)


def check_extensions(engine: Engine, report: CheckReport) -> None:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT extname FROM pg_extension;")).fetchall()
        installed = {row[0] for row in rows}
    for ext in REQUIRED_EXTENSIONS:
        report.record(ext in installed, f"Extensión '{ext}' activa")


def check_tables(engine: Engine, report: CheckReport) -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public';
                """
            )
        ).fetchall()
        present = {row[0] for row in rows}
    for table in REQUIRED_TABLES:
        report.record(table in present, f"Tabla '{table}' existe")


def check_vehicle_seeds(engine: Engine, report: CheckReport) -> None:
    with engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM vehicle_profiles;")).scalar_one()
        codes = {
            row[0]
            for row in conn.execute(text("SELECT code FROM vehicle_profiles;")).fetchall()
        }
        electric_count = conn.execute(
            text("SELECT COUNT(*) FROM vehicle_profiles WHERE is_electric = TRUE;")
        ).scalar_one()

    report.record(count >= 4, f"Semillas de vehículos cargadas (encontrados: {count})")
    report.record("sedan_compacto" in codes, "Perfil 'sedan_compacto' presente")
    report.record("suv_mediana" in codes, "Perfil 'suv_mediana' presente")
    report.record("tractocamion_t3s2" in codes, "Perfil 'tractocamion_t3s2' presente")
    report.record(electric_count >= 1, f"Al menos un perfil eléctrico (encontrados: {electric_count})")


def check_spatial_indexes(engine: Engine, report: CheckReport) -> None:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT tablename
                FROM pg_indexes
                WHERE schemaname = 'public' AND indexdef ILIKE '%USING gist%';
                """
            )
        ).fetchall()
        gist_tables = {row[0] for row in rows}
    for table in REQUIRED_GIST_INDEXED:
        report.record(table in gist_tables, f"Índice GiST presente en '{table}'")


def main() -> int:
    report = CheckReport()
    print("Verificando esquema EcoRuta...")
    try:
        engine = build_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1;"))
    except Exception as exc:  # noqa: BLE001 - reporte explícito de conexión
        print(f"\n[ERROR] No se pudo conectar a la base de datos: {exc}")
        print("¿Ejecutaste `docker compose up -d postgis` y esperaste el healthcheck?\n")
        return 1

    check_extensions(engine, report)
    check_tables(engine, report)
    check_vehicle_seeds(engine, report)
    check_spatial_indexes(engine, report)

    report.print_summary()
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())
