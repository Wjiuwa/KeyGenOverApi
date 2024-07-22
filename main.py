import os
import requests
import hashlib
import time
import asyncio
from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Optional
from dotenv import load_dotenv

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
Client-key = "{self.client_key}"
Authorization-key = "{self.auth_keys.get(base_url_key, 'N/A')}"
Private-key = "{self.private_key}"
Public-key = "{self.public_keys.get(base_url_key, 'N/A')}"
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
    "Internal_ST": os.getenv("BASE_URL4"),
    "Pro_ST": os.getenv("BASE_URL5"),
    "Pro_AM": os.getenv("BASE_URL6")
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
            "Authorization-key": keys_api_client.auth_keys.get(base_url_key),
            "Client-key": keys_api_client.client_key,
            "Private-key": keys_api_client.private_key,
            "Public-key": keys_api_client.public_keys.get(base_url_key)
        } for base_url_key in base_urls
    }

@app.get("/favicon.ico")
async def favicon():
    return Response(status_code=204)  # No Content

@app.get("/api_status/pro_st")
async def get_api_status_pro_st():
    try:
        response = requests.get(f"{base_urls['Pro_ST']}/GetAPIStatus/", timeout=30)  # Ensure the correct endpoint
        if response.status_code == 200 and response.json().get("status") == "success":
            return {"status": "success"}
        else:
            return {"status": "failure"}
    except requests.RequestException:
        return {"status": "failure"}

@app.get("/api_status/pro_am")
async def get_api_status_pro_am():
    try:
        response = requests.get(f"{base_urls['Pro_AM']}/GetAPIStatus/", timeout=30)  # Ensure the correct endpoint
        if response.status_code == 200 and response.json().get("status") == "success":
            return {"status": "success"}
        else:
            return {"status": "failure"}
    except requests.RequestException:
        return {"status": "failure"}

@app.get("/", response_class=HTMLResponse)
async def get_matrix_style_numbers():
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Matrix Effect</title>
        <style>
            body {{
                margin: 0;
                display: flex;
                flex-direction: row;
                justify-content: center;
                align-items: center;
                height: 100vh;
                background: black;
                color: #0F0;
                font-family: monospace;
            }}
            .half {{
                width: 50%;
                height: 100%;
                position: relative;
            }}
            .status {{
                position: absolute;
                top: 20px;
                left: 20px;
                color: white;
                font-size: 20px;
                background-color: rgba(0, 0, 0, 0.7);
                padding: 10px;
                border-radius: 5px;
            }}
            canvas {{
                display: block;
            }}
        </style>
    </head>
    <body>
        <div class="half">
            <canvas id="matrixCanvasST"></canvas>
            <div class="status" id="statusDivST">
                Pro_ST Status: <span id="proStStatus">Loading...</span>
            </div>
        </div>
        <div class="half">
            <canvas id="matrixCanvasAM"></canvas>
            <div class="status" id="statusDivAM">
                Pro_AM Status: <span id="proAmStatus">Loading...</span>
            </div>
        </div>
        <script>
            function createMatrixEffect(canvasId, statusId, apiEndpoint) {{
                const canvas = document.getElementById(canvasId);
                const ctx = canvas.getContext('2d');

                canvas.width = window.innerWidth / 2;
                canvas.height = window.innerHeight;

                const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz';
                const fontSize = 14;
                const columns = canvas.width / fontSize;
                const drops = [];
                for (let x = 0; x < columns; x++) {{
                    drops[x] = 1;
                }}

                function draw() {{
                    ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
                    ctx.fillRect(0, 0, canvas.width, canvas.height);

                    ctx.fillStyle = canvas.style.color || '#0F0';
                    ctx.font = fontSize + 'px monospace';

                    for (let i = 0; i < drops.length; i++) {{
                        const text = chars.charAt(Math.floor(Math.random() * chars.length));
                        ctx.fillText(text, i * fontSize, drops[i] * fontSize);

                        if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {{
                            drops[i] = 0;
                        }}

                        drops[i]++;
                    }}
                }}

                setInterval(draw, 33);

                async function fetchAPIStatus() {{
                    try {{
                        canvas.style.color = 'yellow'; // Change to yellow during the call
                        const response = await fetch(apiEndpoint);
                        const data = await response.json();
                        document.getElementById(statusId).textContent = data.status;

                        if (data.status === 'success') {{
                            canvas.style.color = 'green';
                        }} else {{
                            canvas.style.color = 'red';
                        }}
                    }} catch (error) {{
                        document.getElementById(statusId).textContent = 'error';
                        canvas.style.color = 'pink';
                    }}
                }}

                setInterval(fetchAPIStatus, 20000);
                fetchAPIStatus();
            }}

            createMatrixEffect('matrixCanvasST', 'proStStatus', '/api_status/pro_st');
            createMatrixEffect('matrixCanvasAM', 'proAmStatus', '/api_status/pro_am');
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

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
