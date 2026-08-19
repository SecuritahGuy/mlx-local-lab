import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///service.db")
DEBUG = bool(os.getenv("DEBUG", "false"))  # Deliberate configuration bug: "false" is truthy.
API_RETRIES = int(os.getenv("API_RETRIES", "3"))
