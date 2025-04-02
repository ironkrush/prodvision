import uvicorn
import socket
import os
from dotenv import load_dotenv

load_dotenv()

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('0.0.0.0', port))
            return False
        except socket.error:
            return True

def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    port = start_port
    while is_port_in_use(port) and max_attempts > 0:
        port += 1
        max_attempts -= 1
    if max_attempts == 0:
        raise RuntimeError("Could not find an available port")
    return port

if __name__ == "__main__":
    # Get port from environment variable or use default
    desired_port = int(os.getenv("PORT", "8000"))
    
    # Find an available port starting from the desired port
    port = find_available_port(desired_port)
    if port != desired_port:
        print(f"Port {desired_port} is in use, using port {port} instead")
    
    # Configure uvicorn with optimal settings
    config = {
        "app": "app:app",
        "host": "0.0.0.0",
        "port": port,
        "reload": True,
        "workers": 1,
        "loop": "asyncio",
        "log_level": "info",
        "timeout_keep_alive": 30,
        "backlog": 2048
    }
    
    print(f"Starting server on port {port}")
    uvicorn.run(**config) 