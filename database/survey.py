from datetime import datetime

from pony.orm import Required, StrArray

from database import db
from space_traders_api_client.models import (
    Survey as APISurvey, SurveySize as APISurveySize, SurveyDeposit as APISurveyDeposit
)


class DBSurvey(db.Entity):
    _table_ = "surveys"

    signature = Required(str, index=True)
    deposits: list[str] = Required(StrArray)
    size: str = Required(str)
    expiration: datetime = Required(datetime)

    waypoint: "Waypoint" = Required("DBWaypoint")

    def build_request_body(self) -> APISurvey:
        return APISurvey(
            symbol=self.waypoint.symbol,
            signature=self.signature,
            size=APISurveySize(self.size),
            expiration=self.expiration,
            deposits=[APISurveyDeposit(symbol=symbol) for symbol in self.deposits]
        )
