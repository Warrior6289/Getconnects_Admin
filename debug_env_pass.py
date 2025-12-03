import os
from dotenv import load_dotenv
import urllib.parse

load_dotenv()

db_url = os.getenv("DATABASE_URL")
try:
    # Basic parsing to avoid printing the whole thing if it's huge or confusing
    # URL format: scheme://user:password@host:port/path
    if "@" in db_url:
        user_pass, host_part = db_url.split("@", 1)
        if ":" in user_pass:
            user, password = user_pass.split("://")[1].split(":", 1)
            print(f"Password found: {password}")
            print(f"Is password correct length? {len(password)}")
            print(f"Does it contain $? {'$' in password}")
            print(f"Does it contain vbPua? {'vbPua' in password}")
        else:
            print("Could not split user:password")
    else:
        print("No @ found in URL")
except Exception as e:
    print(f"Error parsing: {e}")
    print(f"Full URL (safe): {db_url.replace(':', 'COLON')}")
