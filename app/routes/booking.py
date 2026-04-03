import json
import os
from flask import Blueprint, request, jsonify
from app.models.booking import Booking, generate_pnr
from app.models.flight import Flight
from config import Config

booking_bp = Blueprint("booking", __name__)

FLIGHTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "flights.json"
)
BOOKINGS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "data", "bookings.json"
)


def _load_json(path: str) -> list:
    with open(path, "r") as f:
        return json.load(f)


def _save_json(path: str, data: list) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


@booking_bp.route("/bookings", methods=["POST"])
def create_booking():
    """
    Simulates a PNR creation request.

    Real-world equivalent:
      - Amadeus: Fare_MasterPricerTravelBoardSearch + PNR_AddMultiElements
      - Sabre:   CreatePassengerNameRecordRQ
      - NDC:     OrderCreateRQ (IATA NDC Level 4)

    The PNR (Passenger Name Record) is the fundamental data unit
    in any GDS. Every booking in Amadeus, Sabre, or IndiGo's own
    DCS is anchored to a 6-character PNR record locator.

    Request body:
    {
      "flight_number": "6E-101",
      "cabin_class": "ECONOMY",
      "passengers": [
        {
          "first_name": "Rahul",
          "last_name": "Sharma",
          "date_of_birth": "1990-05-15",
          "passport_or_id": "AB1234567"
        }
      ]
    }
    """
    body = request.get_json()
    if not body:
        return jsonify({"error": "BAD_REQUEST", "message": "Request body is required"}), 400

    flight_number = body.get("flight_number")
    cabin_class = body.get("cabin_class", "ECONOMY").upper()
    passengers = body.get("passengers", [])

    # Validate required fields
    if not flight_number:
        return jsonify({"error": "BAD_REQUEST", "message": "flight_number is required"}), 400
    if not passengers:
        return jsonify({"error": "BAD_REQUEST", "message": "At least one passenger is required"}), 400
    if len(passengers) > Config.MAX_SEATS_PER_BOOKING:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": f"Maximum {Config.MAX_SEATS_PER_BOOKING} passengers per booking (IATA limit)"
        }), 400

    # Check flight exists and has availability
    all_flights = _load_json(FLIGHTS_PATH)
    target_flight = None
    flight_index = None

    for i, f_data in enumerate(all_flights):
        if f_data["flight_number"] == flight_number:
            target_flight = Flight.from_dict(f_data)
            flight_index = i
            break

    if not target_flight:
        return jsonify({"error": "NOT_FOUND", "message": "Flight not found"}), 404

    cabin_info = target_flight.cabin_classes.get(cabin_class)
    if not cabin_info or cabin_info.available < len(passengers):
        return jsonify({
            "error": "CONFLICT",
            "message": f"Insufficient seats in {cabin_class}. Available: {cabin_info.available if cabin_info else 0}"
        }), 409

    # Calculate fare
    total_fare = cabin_info.fare_INR * len(passengers)

    # Create booking record
    booking = Booking(
        flight_number=flight_number,
        cabin_class=cabin_class,
        passengers=passengers,
        total_fare_INR=total_fare,
        status="CONFIRMED"
    )

    # Update seat inventory
    all_flights[flight_index]["cabin_classes"][cabin_class]["available"] -= len(passengers)
    all_flights[flight_index]["available_seats"] -= len(passengers)
    if all_flights[flight_index]["available_seats"] == 0:
        all_flights[flight_index]["status"] = "SOLD_OUT"

    # Persist
    all_bookings = _load_json(BOOKINGS_PATH)
    all_bookings.append(booking.to_dict())
    _save_json(BOOKINGS_PATH, all_bookings)
    _save_json(FLIGHTS_PATH, all_flights)

    return jsonify({
        "message": "Booking confirmed",
        "pnr": booking.pnr,
        "flight_number": booking.flight_number,
        "cabin_class": booking.cabin_class,
        "passengers": len(passengers),
        "total_fare_INR": booking.total_fare_INR,
        "status": booking.status,
        "booked_at": booking.booked_at
    }), 201


@booking_bp.route("/bookings/<pnr>", methods=["GET"])
def get_booking(pnr):
    """
    Retrieves a booking by its PNR (record locator).

    Real-world equivalent:
      - Amadeus: PNR_Retrieve
      - Sabre:   GetReservationRQ
      - NDC:     OrderRetrieveRQ
    """
    all_bookings = _load_json(BOOKINGS_PATH)

    for b_data in all_bookings:
        if b_data["pnr"] == pnr.upper():
            return jsonify(b_data), 200

    return jsonify({
        "error": "NOT_FOUND",
        "message": f"No booking found with PNR: {pnr}"
    }), 404


@booking_bp.route("/bookings/<pnr>/checkin", methods=["POST"])
def check_in(pnr):
    """
    Simulates web check-in for a booking.

    Real-world equivalent:
      - Amadeus: DCSRCI (Departure Control System Remote Check-In)
      - IndiGo DCS: SITA DCS integration for check-in processing
    """
    all_bookings = _load_json(BOOKINGS_PATH)

    for i, b_data in enumerate(all_bookings):
        if b_data["pnr"] == pnr.upper():
            if b_data["status"] == "CANCELLED":
                return jsonify({
                    "error": "CONFLICT",
                    "message": "Cannot check in a cancelled booking"
                }), 409
            if b_data["status"] == "CHECKED_IN":
                return jsonify({
                    "error": "CONFLICT",
                    "message": "Booking is already checked in"
                }), 409

            all_bookings[i]["status"] = "CHECKED_IN"
            _save_json(BOOKINGS_PATH, all_bookings)

            return jsonify({
                "message": "Check-in successful",
                "pnr": pnr.upper(),
                "status": "CHECKED_IN"
            }), 200

    return jsonify({
        "error": "NOT_FOUND",
        "message": f"No booking found with PNR: {pnr}"
    }), 404


@booking_bp.route("/bookings/<pnr>/cancel", methods=["POST"])
def cancel_booking(pnr):
    """
    Cancels a booking and restores seat inventory.

    Real-world equivalent:
      - Amadeus: PNR_Cancel
      - Sabre:   OTA_CancelRQ
      - NDC:     OrderCancelRQ
    """
    all_bookings = _load_json(BOOKINGS_PATH)
    all_flights = _load_json(FLIGHTS_PATH)

    for i, b_data in enumerate(all_bookings):
        if b_data["pnr"] == pnr.upper():
            if b_data["status"] == "CANCELLED":
                return jsonify({
                    "error": "CONFLICT",
                    "message": "Booking is already cancelled"
                }), 409

            # Restore seat inventory
            flight_number = b_data["flight_number"]
            cabin_class = b_data["cabin_class"]
            num_passengers = len(b_data["passengers"])

            for j, f_data in enumerate(all_flights):
                if f_data["flight_number"] == flight_number:
                    all_flights[j]["cabin_classes"][cabin_class]["available"] += num_passengers
                    all_flights[j]["available_seats"] += num_passengers
                    if all_flights[j]["status"] == "SOLD_OUT":
                        all_flights[j]["status"] = "SCHEDULED"
                    break

            all_bookings[i]["status"] = "CANCELLED"
            _save_json(BOOKINGS_PATH, all_bookings)
            _save_json(FLIGHTS_PATH, all_flights)

            return jsonify({
                "message": "Booking cancelled",
                "pnr": pnr.upper(),
                "status": "CANCELLED"
            }), 200

    return jsonify({
        "error": "NOT_FOUND",
        "message": f"No booking found with PNR: {pnr}"
    }), 404
