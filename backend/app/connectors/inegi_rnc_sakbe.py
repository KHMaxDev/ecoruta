"""Cliente de la API SAKBÉ v3.1 del INEGI (Red Nacional de Caminos).

Se utiliza como referencia oficial de rutas y validación de tarifas de casetas
en México. Requiere un token de acceso (``INEGI_SAKBE_TOKEN``).
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger("ecoruta.connectors.inegi_sakbe")


class InegiSakbeConnector:
    """Cliente para la API Oficial SAKBÉ v3.1 del INEGI."""

    BASE_URL = "https://gaia.inegi.org.mx/sakbe_v3.1"

    def __init__(self, api_token: str) -> None:
        self.api_token = api_token

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def fetch_reference_route(
        self,
        dest_i_id: int,
        dest_f_id: int,
        vehicle_type: int = 1,
        opt_criteria: str = "optimo",
    ) -> dict[str, Any]:
        """Obtiene una ruta de referencia oficial.

        Args:
            dest_i_id: Identificador INEGI del nodo origen.
            dest_f_id: Identificador INEGI del nodo destino.
            vehicle_type: 1 = Automóvil, 5 = Camión 5 ejes.
            opt_criteria: ``optimo``, ``libre`` o ``cuota``.
        """
        if opt_criteria not in {"optimo", "libre", "cuota"}:
            raise ValueError(f"Criterio no soportado: {opt_criteria}")

        url = f"{self.BASE_URL}/{opt_criteria}"
        payload = {
            "dest_i": dest_i_id,
            "dest_f": dest_f_id,
            "v": vehicle_type,
            "type": "json",
            "proj": "GRS80",
            "key": self.api_token,
        }
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(url, data=payload)
            resp.raise_for_status()
            return resp.json()
