import os

class Config:
    """Base configuration."""
    DEBUG = False
    TESTING = False
    # In a real PSS/GDS system this would be an IATA BSP endpoint or
    # Amadeus/Sabre host. Here we use static mock data to simulate
    # the contract shape of those responses.
    MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), "app", "data")
    MAX_SEATS_PER_BOOKING = 9  # IATA standard limit per PNR

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True
    DEBUG = True
