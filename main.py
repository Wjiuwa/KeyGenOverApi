import os
import requests
import hashlib
import time
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
import asyncio

# Load environment variables from .env file
load_dotenv()

class GetKeys:
    def __init__(self, base_urls: Dict[str, str]):
        self.base_urls = base_urls
        self.client_key = os.getenv("CLIENT_KEY")
        self.private_key = os.getenv("PRIVATE_KEY")
        self.auth_keys = {}
        self.last_key_generation_time = {}
        self.public_keys = {}

    def get_public_key(self, base_url_key: str) -> Optional[str]:
        try:
            url = f"{self.base_urls[base_url_key]}/GetKey/{self.client_key}/"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                json_response = response.json()
                if json_response.get("status") == "success":
                    result = json_response.get("result", [])
                    if result and "Security" in result[0] and result[0]["Security"]:
                        security_info = result[0]["Security"]
                        if security_info:
                            self.public_keys[base_url_key] = security_info[0].get("PublicKey")
                            if self.public_keys[base_url_key]:
                                self.save_keys_to_file()
                                return self.public_keys[base_url_key]
            return None
        except requests.exceptions.RequestException as e:
            print(f"An error occurred with {base_url_key}: {e}")
            return None

    def generate_auth_key(self, base_url_key: str) -> Optional[str]:
        if not self.public_keys.get(base_url_key):
            self.get_public_key(base_url_key)
        if self.public_keys.get(base_url_key) is None:
            return None
        data = self.public_keys[base_url_key] + self.client_key + self.private_key
        self.auth_keys[base_url_key] = hashlib.sha256(data.encode()).hexdigest()
        self.last_key_generation_time[base_url_key] = time.time()
        self.save_keys_to_file()
        return self.auth_keys[base_url_key]

    def save_keys_to_file(self):
        keys_data = ""
        for base_url_key in self.base_urls:
            keys_data += f"""
[{base_url_key}]
client_key = "{self.client_key}"
authorization_key = "{self.auth_keys.get(base_url_key, 'N/A')}"
private_key = "{self.private_key}"
public_key = "{self.public_keys.get(base_url_key, 'N/A')}"
"""
        with open("data/keys.txt", "w") as file:
            file.write(keys_data)

    def make_request(self, base_url_key: str, endpoint: str):
        if (
            self.last_key_generation_time.get(base_url_key) is None
            or time.time() - self.last_key_generation_time[base_url_key] >= 1800
        ):
            self.generate_auth_key(base_url_key)
        if self.auth_keys.get(base_url_key) is None:
            return {"error": f"Failed to generate auth key for {base_url_key}"}
        headers = {"Authorization-Key": self.auth_keys[base_url_key], "Client-Key": self.client_key}
        response = requests.get(f"{self.base_urls[base_url_key]}/{endpoint}", headers=headers)
        if response.status_code == 200:
            return response.json()
        return {"error": f"Request to {base_url_key} failed"}

# Initialize GetKeys with all base URLs
base_urls = {
    "External_AM": os.getenv("BASE_URL1"),
    "External_ST": os.getenv("BASE_URL2"),
    "Internal_AM": os.getenv("BASE_URL3"),
    "Internal_ST": os.getenv("BASE_URL4")
}

keys_api_client = GetKeys(base_urls)

# FastAPI app
app = FastAPI()

# Allow CORS from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/keys")
async def get_keys():
    return {
        base_url_key: {
            "client_key": keys_api_client.client_key,
            "authorization_key": keys_api_client.auth_keys.get(base_url_key),
            "private_key": keys_api_client.private_key,
            "public_key": keys_api_client.public_keys.get(base_url_key)
        } for base_url_key in base_urls
    }

async def refresh_keys():
    while True:
        for base_url_key in base_urls:
            keys_api_client.get_public_key(base_url_key)
            keys_api_client.generate_auth_key(base_url_key)
        await asyncio.sleep(1800)  # Sleep for 30 minutes

@app.on_event("startup")
async def on_startup():
    asyncio.create_task(refresh_keys())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
