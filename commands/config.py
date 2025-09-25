#  commands/config.py
import os
from dotenv import load_dotenv

load_dotenv()


SUPER_ADMIN_ID = int(os.getenv("SUPER_ADMIN_ID"))