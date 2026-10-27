"""Геохелпери на основі PostGIS.

Координати зберігаються як звичайні колонки lat/lng, а для геозапитів
будується вираз geography-точки. Той самий вираз проіндексовано GiST-індексом
(див. міграцію 0001), тому ВАЖЛИВО, щоб geo_point() генерував рівно такий SQL:
    CAST(ST_SetSRID(ST_MakePoint(lng, lat), 4326) AS geography)
"""

from sqlalchemy import Float, func, literal, literal_column
from sqlalchemy.sql.elements import ColumnElement
from sqlalchemy.types import UserDefinedType


class Geography(UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw) -> str:
        return "geography"


# Рендериться як константа, а не параметр, щоб вираз збігався з індексом.
_SRID_WGS84 = literal_column("4326")


def geo_point(lat, lng) -> ColumnElement:
    return func.ST_SetSRID(func.ST_MakePoint(lng, lat), _SRID_WGS84).cast(Geography())


def geo_point_value(lat: float, lng: float) -> ColumnElement:
    return geo_point(literal(lat, Float), literal(lng, Float))
