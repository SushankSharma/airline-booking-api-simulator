from dataclasses import dataclass, field
from typing import Dict


@dataclass
class CabinClass:
    """
    Represents a single cabin class on a flight.
    In a real GDS contract (Amadeus, Sabre), this maps to
    a Fare Basis Code with associated RBD (Reservation Booking Designator).
    """
    available: int
    fare_INR: float


@dataclass
class Flight:
    """
    Mirrors the data shape returned by a PSS availability response.
    Real-world equivalent: Amadeus Air_MultiAvailability reply,
    or Sabre BargainFinderMax response.
    """
    flight_number: str
    origin: str          # IATA airport code
    destination: str     # IATA airport code
    departure: str       # ISO 8601
    arrival: str         # ISO 8601
    aircraft_type: str
    total_seats: int
    available_seats: int
    cabin_classes: Dict[str, CabinClass]
    status: str          # SCHEDULED | SOLD_OUT | CANCELLED

    @classmethod
    def from_dict(cls, data: dict) -> "Flight":
        cabin_classes = {
            k: CabinClass(**v)
            for k, v in data["cabin_classes"].items()
        }
        return cls(
            flight_number=data["flight_number"],
            origin=data["origin"],
            destination=data["destination"],
            departure=data["departure"],
            arrival=data["arrival"],
            aircraft_type=data["aircraft_type"],
            total_seats=data["total_seats"],
            available_seats=data["available_seats"],
            cabin_classes=cabin_classes,
            status=data["status"]
        )
