from app import db
from app.models import base_model
from sqlalchemy import PrimaryKeyConstraint


class Report(base_model.BaseModel):
    '''
    Clase reporte de totales en un mes
    '''
    __tablename__ = 'report'
    year = db.Column(db.Integer)
    month = db.Column(db.Integer)
    type = db.Column(db.String)
    carrier_id = db.Column(db.Integer, db.ForeignKey('carriers.id'))
    quantity = db.Column(db.Integer)
    __table_args__= (PrimaryKeyConstraint("year","month","type","carrier_id",name = "region_pk"),{})

    def __init__(self, year, month, type, carrier_id, quantity):
        self.year = year
        self.month = month
        self.type = type
        self.carrier_id = carrier_id
        self.quantity = quantity
