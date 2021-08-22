from typing import TypedDict

import datetime


class RelatedPatientCreateData(TypedDict):
    first_name: str
    last_name: str
    patronymic: str
    birth_date: datetime.date
    gender: str
    type: str  # relation type


class RelatedPatientUpdateData(TypedDict):
    first_name: str
    last_name: str
    patronymic: str
    birth_date: datetime.date
    gender: str
    type: str  # relation type
    id: int  # relation id
