import uuid
import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from typing import List


def generate_pnr() -> str:
    """
    Generates a 6-character alphanumeric PNR.
    Real PNRs in Amadeus GDS follow this same format.
    IndiGo uses this structure in their DCS (Departure Control System).
    """
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))


@dataclass
class Passenger:
    first_name: str
    last_name: str
    date_of_birth: str   # YYYY-MM-DD
    passport_or_id: str


@dataclass
class Booking:
    """
    Represents a confirmed booking record (PNR).
    In a real PSS, this is stored in the host system and
    accessible via the GDS using the record locator (PNR code).
    """
    pnr: str = field(default_factory=generate_pnr)
    flight_number: str = ""
    cabin_class: str = "ECONOMY"
    passengers: List[Passenger] = field(default_factory=list)
    total_fare_INR: float = 0.0
    status: str = "CONFIRMED"   # CONFIRMED | CHECKED_IN | CANCELLED
    booked_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )

    @classmethod
    def from_dict(cls, data: dict) -> "Booking":
        passengers = [Passenger(**p) for p in data.get("passengers", [])]
        return cls(
            pnr=data.get("pnr", generate_pnr()),
            flight_number=data["flight_number"],
            cabin_class=data.get("cabin_class", "ECONOMY"),
            passengers=passengers,
            total_fare_INR=data.get("total_fare_INR", 0.0),
            status=data.get("status", "CONFIRMED"),
            booked_at=data.get("booked_at", datetime.utcnow().isoformat())
        )

    def to_dict(self) -> dict:
        return {
            "pnr": self.pnr,
            "flight_number": self.flight_number,
            "cabin_class": self.cabin_class,
            "passengers": [
                p.__dict__ if hasattr(p, "__dict__") and not isinstance(p, dict) else p
                for p in self.passengers
            ],
            "total_fare_INR": self.total_fare_INR,
            "status": self.status,
            "booked_at": self.booked_at
        }
