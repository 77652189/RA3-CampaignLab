"""ParkingPlaceBehavior (E157 / E188, bench 2026-11-15, checks/engine_parking.readings.toml): the airfield's room for
LIMITED_PRODUCTION_AIRCRAFT -- LimitedProductionAircraftSpots (default 0). The host's order (Production.admits) queues
such a plane only at a factory whose spots outnumber its planes of that kind alive and queued; none without the module.

Data only. Taking the spot at the order (a queued one holds it) is INFERRED: the bench reads only the count made.
Not modelled: NumRows / NumCols and the slots, landing, returning, CanParkHereFilter, the carrier's."""
from engine.kernel import factory, interfaces, module
from engine.ports import templates


class ParkingData(module.ModuleData):
    def __init__(self, spots=0):
        self.spots = spots

    @classmethod
    def parse(cls, head, inner):
        return cls(int(templates.num(templates.attr(head, 'LimitedProductionAircraftSpots'), 0.0)))


@factory.module('ParkingPlaceBehavior')
class Parking(module.Module, interfaces.Parking):
    DATA = ParkingData

    @property
    def spots(self):
        return self.data.spots
