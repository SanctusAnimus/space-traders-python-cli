from pony.orm import PrimaryKey, Optional, Json, Required

from database import db


class DBShip(db.Entity):
    _table_ = "ships"

    symbol = PrimaryKey(str, auto=False)
    role: str = Required(str)

    flight_mode = Required(str)
    status = Required(str)

    cargo_capacity = Required(int)

    fuel_current = Required(int)
    fuel_capacity = Required(int)

    frame = Optional(Json)
    reactor = Optional(Json)
    engine = Optional(Json)
    modules = Optional(Json)
    mounts = Optional(Json)
