"""Capa 1: Conectores e ingesta de datos oficiales de México (INEGI, CNE, CONAGUA, SESNSP)."""

from app.connectors.cne_combustible import CNEFuelConnector
from app.connectors.conagua_riesgos import WeatherAndFloodHazardConnector
from app.connectors.inegi_rnc_sakbe import InegiSakbeConnector
from app.connectors.sesnsp_seguridad import SESNSPTerritorialContextService

__all__ = [
    "CNEFuelConnector",
    "WeatherAndFloodHazardConnector",
    "InegiSakbeConnector",
    "SESNSPTerritorialContextService",
]
