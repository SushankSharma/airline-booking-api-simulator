import json
import os
from flask import Blueprint, request, jsonify
from app.models.flight import Flight

availability_bp = Blueprint("availability", __name__)

def _load_flights() -> list:
    path = os.path.join(
        os.path.dirname(__file__), "..", "data", "flights.json"
    )
    with open(path, "r") as f:
        return json.load(f)


@availability_bp.route("/flights/availability", methods=["GET"])
def get_availability():
    """
    Simulates a GDS availability query.

    Real-world equivalent:
      - Amadeus: Air_MultiAvailability request
      - Sabre:   OTA_AirAvailRQ (OpenTravel Alliance schema)
      - NDC:     AirShoppingRQ (IATA NDC Level 4)

    Query params:
      origin      -- IATA code (e.g. DEL)
      destination -- IATA code (e.g. BOM)
      date        -- YYYY-MM-DD
      cabin       -- ECONOMY | BUSINESS (optional, default ECONOMY)
    """
    origin = request.args.get("origin", "").upper()
    destination = request.args.get("destination", "").upper()
    date = request.args.get("date", "")
    cabin = request.args.get("cabin", "ECONOMY").upper()

    # Input validation — mirrors what a real PSS would reject
    if not origin or not destination or not date:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "origin, destination, and date are required"
        }), 400

    if origin == destination:
        return jsonify({
            "error": "BAD_REQUEST",
            "message": "origin and destination cannot be the same"
        }), 400

    all_flights = _load_flights()
    results = []

    for f_data in all_flights:
        flight = Flight.from_dict(f_data)
        # Match on origin, destination, and date prefix
        if (
            flight.origin == origin
            and flight.destination == destination
            and flight.departure.startswith(date)
            and flight.status == "SCHEDULED"
        ):
            cabin_info = flight.cabin_classes.get(cabin)
            results.append({
                "flight_number": flight.flight_number,
                "origin": flight.origin,
                "destination": flight.destination,
                "departure": flight.departure,
                "arrival": flight.arrival,
                "aircraft_type": flight.aircraft_type,
                "cabin": cabin,
                "available_seats": cabin_info.available if cabin_info else 0,
                "fare_INR": cabin_info.fare_INR if cabin_info else None,
                "status": flight.status
            })

    if not results:
        return jsonify({
            "flights": [],
            "message": "No available flights found for this route and date"
        }), 200

    return jsonify({
        "flights": results,
        "count": len(results)
    }), 200
