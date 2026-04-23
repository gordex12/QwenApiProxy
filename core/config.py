import os
from dotenv import load_dotenv, set_key

ENV_FILE = ".env"

def load_config():
    """Load environment variables from the .env file."""
    load_dotenv(ENV_FILE)

def get_qwen_token() -> str:
    """Retrieve the QWEN_TOKEN from environment variables."""
    return os.getenv("QWEN_TOKEN")

def set_qwen_token(token: str):
    """Save the provided token into the .env file and update the current environment."""
    if not os.path.exists(ENV_FILE):
        with open(ENV_FILE, 'w') as f:
            f.write("")
    
    # Use python-dotenv set_key to update .env safely
    set_key(ENV_FILE, "QWEN_TOKEN", token)
    
    # Update current environment variable
    os.environ["QWEN_TOKEN"] = token
