from pony.orm import StrArray, Json, PrimaryKey, Optional, Required, Set

from database import db


class DBSystem(db.Entity):
    _table_ = "systems"

    symbol: str = PrimaryKey(str, auto=False)
    sector: str = Optional(str)
    coord_x: int = Required(int)
    coord_y: int = Required(int)
    type: str = Required(str)

    waypoints: list["DBWaypoint"] | Set = Set("DBWaypoint")


class DBWaypoint(db.Entity):
    _table_ = "waypoints"

    symbol: str = PrimaryKey(str, auto=False)
    type: str = Required(str)
    coord_x: int = Required(int)
    coord_y: int = Required(int)
    faction: str = Optional(str, nullable=True)
    traits: list[str] = Required(StrArray)
    chart: bool | None = Optional(bool, sql_default=False)

    system: "DBSystem" = Required(DBSystem)

    # market trades
    trades: list["DBMarketTrade"] | Set = Set("DBMarketTrade")
    # shipyard trades
    ships: list["DBShipyardTrade"] | Set = Set("DBShipyardTrade")
    # gateway systems
    connected_systems: list["DBWaypoint"] | Set = Set("DBSystem")

    surveys: list["DBSurvey"]


class DBMarketTrade(db.Entity):
    _table_ = "market_trades"
    resource_symbol: str = Required(str, auto=False, index=True)
    trade_volume: int = Required(int)
    supply: int = Required(int)
    purchase_price: int = Required(int)
    sell_price: int = Required(int)


class DBShipyardTrade(db.Entity):
    _table_ = "shipyard_trades"
    type = Required(str, auto=False, index=True)

    purchase_price: int = Required(int)

    # this is not great, ngl
    frame = Optional(Json)
    reactor = Optional(Json)
    engine = Optional(Json)
    modules = Optional(Json)
    mounts = Optional(Json)
