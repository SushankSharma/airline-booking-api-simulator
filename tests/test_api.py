import json
import os
import shutil
import pytest
from app import create_app
from config import TestingConfig

# Paths to the test data files
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "data")
FLIGHTS_PATH = os.path.join(DATA_DIR, "flights.json")
BOOKINGS_PATH = os.path.join(DATA_DIR, "bookings.json")

# Keep a backup of original data to restore after tests
FLIGHTS_BACKUP = os.path.join(DATA_DIR, "flights.backup.json")
BOOKINGS_BACKUP = os.path.join(DATA_DIR, "bookings.backup.json")


@pytest.fixture(autouse=True)
def reset_data():
    """Reset mock data before each test to ensure isolation."""
    # Backup originals
    shutil.copy(FLIGHTS_PATH, FLIGHTS_BACKUP)
    shutil.copy(BOOKINGS_PATH, BOOKINGS_BACKUP)
    # Reset bookings to empty
    with open(BOOKINGS_PATH, "w") as f:
        json.dump([], f)
    # Reset flights to known state
    with open(FLIGHTS_PATH, "r") as f:
        flights = json.load(f)
    # Restore original seat counts
    original_flights = [
        {
            "flight_number": "6E-101",
            "origin": "DEL",
            "destination": "BOM",
            "departure": "2026-04-10T06:00:00",
            "arrival": "2026-04-10T08:15:00",
            "aircraft_type": "A320",
            "total_seats": 180,
            "available_seats": 42,
            "cabin_classes": {
                "ECONOMY": {"available": 38, "fare_INR": 4500},
                "BUSINESS": {"available": 4, "fare_INR": 12000}
            },
            "status": "SCHEDULED"
        },
        {
            "flight_number": "6E-202",
            "origin": "BOM",
            "destination": "BLR",
            "departure": "2026-04-10T09:30:00",
            "arrival": "2026-04-10T11:00:00",
            "aircraft_type": "A320",
            "total_seats": 180,
            "available_seats": 15,
            "cabin_classes": {
                "ECONOMY": {"available": 12, "fare_INR": 3800},
                "BUSINESS": {"available": 3, "fare_INR": 9500}
            },
            "status": "SCHEDULED"
        },
        {
            "flight_number": "6E-303",
            "origin": "DEL",
            "destination": "BLR",
            "departure": "2026-04-10T14:00:00",
            "arrival": "2026-04-10T17:30:00",
            "aircraft_type": "A321",
            "total_seats": 220,
            "available_seats": 0,
            "cabin_classes": {
                "ECONOMY": {"available": 0, "fare_INR": 5200},
                "BUSINESS": {"available": 0, "fare_INR": 14000}
            },
            "status": "SOLD_OUT"
        },
        {
            "flight_number": "6E-404",
            "origin": "HYD",
            "destination": "DEL",
            "departure": "2026-04-10T18:45:00",
            "arrival": "2026-04-10T21:00:00",
            "aircraft_type": "A320",
            "total_seats": 180,
            "available_seats": 91,
            "cabin_classes": {
                "ECONOMY": {"available": 88, "fare_INR": 4100},
                "BUSINESS": {"available": 3, "fare_INR": 11000}
            },
            "status": "SCHEDULED"
        }
    ]
    with open(FLIGHTS_PATH, "w") as f:
        json.dump(original_flights, f, indent=2)

    yield

    # Restore backups
    shutil.move(FLIGHTS_BACKUP, FLIGHTS_PATH)
    shutil.move(BOOKINGS_BACKUP, BOOKINGS_PATH)


@pytest.fixture
def client():
    app = create_app(TestingConfig)
    with app.test_client() as client:
        yield client


# ─── Availability Tests ─────────────────────────────────────────

class TestAvailability:
    def test_valid_availability_query(self, client):
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=BOM&date=2026-04-10"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["count"] >= 1
        assert data["flights"][0]["flight_number"] == "6E-101"

    def test_availability_missing_params(self, client):
        resp = client.get("/api/v1/flights/availability?origin=DEL")
        assert resp.status_code == 400
        assert "required" in resp.get_json()["message"]

    def test_availability_same_origin_dest(self, client):
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=DEL&date=2026-04-10"
        )
        assert resp.status_code == 400
        assert "same" in resp.get_json()["message"]

    def test_availability_no_results(self, client):
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=MAA&date=2026-04-10"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["flights"] == []

    def test_availability_business_cabin(self, client):
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=BOM&date=2026-04-10&cabin=BUSINESS"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["flights"][0]["cabin"] == "BUSINESS"
        assert data["flights"][0]["fare_INR"] == 12000

    def test_sold_out_flight_not_returned(self, client):
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=BLR&date=2026-04-10"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        # 6E-303 is SOLD_OUT, should not appear
        assert data["flights"] == []


# ─── Booking Tests ───────────────────────────────────────────────

class TestBooking:
    def test_create_booking_success(self, client):
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-101",
            "cabin_class": "ECONOMY",
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["status"] == "CONFIRMED"
        assert len(data["pnr"]) == 6
        assert data["total_fare_INR"] == 4500

    def test_create_booking_missing_body(self, client):
        resp = client.post("/api/v1/bookings",
                           data="",
                           content_type="application/json")
        assert resp.status_code == 400

    def test_create_booking_missing_flight(self, client):
        resp = client.post("/api/v1/bookings", json={
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        assert resp.status_code == 400

    def test_create_booking_no_passengers(self, client):
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-101",
            "passengers": []
        })
        assert resp.status_code == 400

    def test_create_booking_flight_not_found(self, client):
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "XX-999",
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        assert resp.status_code == 404

    def test_create_booking_insufficient_seats(self, client):
        # 6E-202 BUSINESS has only 3 seats
        passengers = [
            {
                "first_name": f"Pax{i}",
                "last_name": "Test",
                "date_of_birth": "1990-01-01",
                "passport_or_id": f"ID{i}"
            }
            for i in range(5)
        ]
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-202",
            "cabin_class": "BUSINESS",
            "passengers": passengers
        })
        assert resp.status_code == 409

    def test_get_booking_by_pnr(self, client):
        # First create a booking
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-101",
            "cabin_class": "ECONOMY",
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        pnr = resp.get_json()["pnr"]

        # Retrieve it
        resp = client.get(f"/api/v1/bookings/{pnr}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["pnr"] == pnr
        assert data["flight_number"] == "6E-101"

    def test_get_booking_not_found(self, client):
        resp = client.get("/api/v1/bookings/ZZZZZ1")
        assert resp.status_code == 404


# ─── Check-in Tests ──────────────────────────────────────────────

class TestCheckIn:
    def _create_booking(self, client):
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-101",
            "cabin_class": "ECONOMY",
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        return resp.get_json()["pnr"]

    def test_checkin_success(self, client):
        pnr = self._create_booking(client)
        resp = client.post(f"/api/v1/bookings/{pnr}/checkin")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "CHECKED_IN"

    def test_checkin_already_checked_in(self, client):
        pnr = self._create_booking(client)
        client.post(f"/api/v1/bookings/{pnr}/checkin")
        resp = client.post(f"/api/v1/bookings/{pnr}/checkin")
        assert resp.status_code == 409

    def test_checkin_cancelled_booking(self, client):
        pnr = self._create_booking(client)
        client.post(f"/api/v1/bookings/{pnr}/cancel")
        resp = client.post(f"/api/v1/bookings/{pnr}/checkin")
        assert resp.status_code == 409

    def test_checkin_not_found(self, client):
        resp = client.post("/api/v1/bookings/ZZZZZ1/checkin")
        assert resp.status_code == 404


# ─── Cancel Tests ─────────────────────────────────────────────────

class TestCancel:
    def _create_booking(self, client):
        resp = client.post("/api/v1/bookings", json={
            "flight_number": "6E-101",
            "cabin_class": "ECONOMY",
            "passengers": [{
                "first_name": "Rahul",
                "last_name": "Sharma",
                "date_of_birth": "1990-05-15",
                "passport_or_id": "AB1234567"
            }]
        })
        return resp.get_json()["pnr"]

    def test_cancel_success(self, client):
        pnr = self._create_booking(client)
        resp = client.post(f"/api/v1/bookings/{pnr}/cancel")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "CANCELLED"

    def test_cancel_already_cancelled(self, client):
        pnr = self._create_booking(client)
        client.post(f"/api/v1/bookings/{pnr}/cancel")
        resp = client.post(f"/api/v1/bookings/{pnr}/cancel")
        assert resp.status_code == 409

    def test_cancel_restores_inventory(self, client):
        # Check initial availability
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=BOM&date=2026-04-10"
        )
        initial_seats = resp.get_json()["flights"][0]["available_seats"]

        # Book and then cancel
        pnr = self._create_booking(client)
        client.post(f"/api/v1/bookings/{pnr}/cancel")

        # Check availability is restored
        resp = client.get(
            "/api/v1/flights/availability?origin=DEL&destination=BOM&date=2026-04-10"
        )
        final_seats = resp.get_json()["flights"][0]["available_seats"]
        assert final_seats == initial_seats

    def test_cancel_not_found(self, client):
        resp = client.post("/api/v1/bookings/ZZZZZ1/cancel")
        assert resp.status_code == 404
