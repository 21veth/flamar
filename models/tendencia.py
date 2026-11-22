from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class PuntoInteres:
    fecha: date
    valor: int | None
    original: str
    parcial: bool = False


@dataclass(frozen=True)
class SerieInteres:
    termino: str
    pais: str
    granularidad: str
    puntos: tuple[PuntoInteres, ...]
    archivo: str
    huella: str
    url: str


@dataclass(frozen=True)
class AnalisisTendencia:
    estado: str
    interes: float | None
    crecimiento: float | None
    motivo: str
    reciente: bool = False
