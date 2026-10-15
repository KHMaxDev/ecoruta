"""Modelos de persistencia (SQLAlchemy 2.0).

El esquema espacial se define en ``database/init_db.sql`` (PostGIS/pgRouting).
Aquí solo se documenta el mapeo ORM de la tabla de perfiles vehiculares, que es
la única consultada directamente por la API.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Clase base declarativa de SQLAlchemy 2.0."""


class VehicleProfile(Base):
    __tablename__ = "vehicle_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)
    name: Mapped[str]
    fuel_type: Mapped[str]
    empty_mass_kg: Mapped[float]
    frontal_area_m2: Mapped[float]
    drag_coeff_cd: Mapped[float]
    rolling_coeff_crr: Mapped[float]
    drivetrain_efficiency: Mapped[float]
    idle_power_watts: Mapped[float]
    nominal_kml: Mapped[float]
    num_axles: Mapped[int]
    height_m: Mapped[float]
    max_weight_tons: Mapped[float]
