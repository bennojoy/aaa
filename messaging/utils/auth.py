import logging
import httpx
from ..config import SYSTEM_PHONE, SYSTEM_PASSWORD

async def signup_system_user():
    """Try to sign up the system user. Ignore error if user already exists."""
    url = "http://localhost:8000/api/v1/auth/signup"
    data = {
        "phone_number": SYSTEM_PHONE,
        "password": SYSTEM_PASSWORD,
        "alias": "system_user",
        "user_type": "human",
        "language": "en"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=data)
            if response.status_code == 200:
                logging.info("System user signed up successfully.")
            elif response.status_code == 400 and ("already exists" in response.text or "exists" in response.text):
                logging.info("System user already exists, continuing.")
            else:
                logging.warning(f"System user signup response: {response.text}")
        except Exception as e:
            logging.error(f"System user signup error: {e}")

async def get_system_token() -> str:
    """Get system token for API calls"""
    # Ensure system user exists
    await signup_system_user()
    url = "http://localhost:8000/api/v1/auth/signin"
    data = {
        "identifier": SYSTEM_PHONE,
        "password": SYSTEM_PASSWORD
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data)
        response.raise_for_status()
        return response.json()["access_token"] 