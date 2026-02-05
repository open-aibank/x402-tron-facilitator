import os
from dotenv import load_dotenv

load_dotenv()

# PrivateKey Configuration
PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")

# FeeTo Address
FEE_TO_ADDRESS = os.getenv("FEE_TO_ADDRESS", "")

# Base fee
BASE_FEE = os.getenv("BASE_FEE", 0)
