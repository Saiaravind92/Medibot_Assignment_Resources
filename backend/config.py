import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory of backend
BASE_DIR = Path(__file__).resolve().parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Resource Paths
DATA_DIR = Path("c:/Users/saiar/Downloads/Medibot_Assignment_Resources/mediassist_data")
DB_PATH = DATA_DIR / "db" / "mediassist.db"
QDRANT_PATH = BASE_DIR / "qdrant_db"
QDRANT_COLLECTION = "mediassist_documents"

# Access Matrix: maps each role to the collections it can read
ROLE_COLLECTIONS = {
    "doctor": ["general", "clinical", "nursing"],
    "nurse": ["general", "nursing"],
    "billing_executive": ["general", "billing"],
    "technician": ["general", "equipment"],
    "admin": ["general", "clinical", "nursing", "billing", "equipment"]
}

# Mapping directories to collections
DIR_COLLECTIONS = {
    "general": "general",
    "clinical": "clinical",
    "nursing": "nursing",
    "billing": "billing",
    "equipment": "equipment"
}
