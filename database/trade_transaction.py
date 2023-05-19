from datetime import datetime

from pony.orm import Required, PrimaryKey

from database import db


class DBTradeTransaction(db.Entity):
    _table_ = "trade_transactions"

    id = PrimaryKey(int, size=64, auto=True)
    ship = Required("DBShip")
    type: str = Required(str)
    resource_symbol: str = Required(str)
    units: int = Required(int)
    cost: int = Required(int)

    when: datetime = Required(datetime)

