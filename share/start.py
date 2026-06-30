# -*- coding: utf-8 -*-
import os
import sys
import subprocess
import json
import time
import webbrowser
import threading
import platform


def is_admin():
    if platform.system() != "Windows":
        return True
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def restart_as_admin():
    if platform.system() != "Windows":
        return
    try:
        import ctypes
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            sys.argv[0],
            os.path.dirname(os.path.abspath(__file__)),
            1
        )
        sys.exit(0)
    except Exception as e:
        print(f"Failed to restart as admin: {e}")


def setup_firewall(port):
    if platform.system() != "Windows":
        return
    if not is_admin():
        return
    rule_name = "WiFi-SPI Controller"
    try:
        subprocess.run(
            ["netsh", "advfirewall", "firewall", "delete", "rule", "name={}".format(rule_name)],
            capture_output=True,
            text=True
        )
        result = subprocess.run(
            ["netsh", "advfirewall", "firewall", "add", "rule",
             "name={}".format(rule_name),
             "dir=in",
             "action=allow",
             "protocol=TCP",
             "localport={}".format(port)],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print(f"Firewall rule added: {rule_name} (TCP port {port})")
        else:
            print(f"Warning: Failed to add firewall rule: {result.stderr.strip()}")
    except Exception as e:
        print(f"Warning: Firewall configuration failed: {e}")


def install_requirements():
    """Install dependencies from requirements.txt"""
    print("Checking dependencies...")
    try:
        import fastapi
        import uvicorn
        import inputs
        print("Dependencies already installed.")
        return True
    except ImportError:
        print("Missing dependencies detected.")
    
    req_file = "requirements.txt"
    if not os.path.exists(req_file):
        print(f"Error: {req_file} not found!")
        with open(req_file, "w") as f:
            f.write("fastapi\nuvicorn\ninputs\npydantic\nwebsockets\n")
        print(f"Created default {req_file}")
        
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "--version"], stdout=subprocess.DEVNULL)
        
        print("Installing from requirements.txt...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", req_file])
        print("Dependencies installed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e}")
        return False
    except FileNotFoundError:
        print("Error: 'pip' not found. Please ensure Python is installed correctly with pip.")
        return False

def load_config():
    """Load configuration from config.json"""
    config_file = "config.json"
    default_config = {"host": "0.0.0.0", "port": 8000}
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    return default_config

def start_backend():
    """Start the FastAPI backend"""
    print("Starting backend server...")
    
    try:
        import uvicorn
        current_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.join(current_dir, 'api')
        if current_dir not in sys.path:
            sys.path.append(current_dir)
        if api_dir not in sys.path:
             sys.path.append(api_dir)

        from api.main import app, HOST, PORT
        
        print(f"Server running at http://{HOST}:{PORT}")
        
        def open_browser():
            time.sleep(2)
            webbrowser.open(f"http://localhost:{PORT}") 
            
        threading.Thread(target=open_browser).start()
        
        uvicorn.run(app, host=HOST, port=PORT)
        
    except ImportError as e:
        print(f"Error importing uvicorn or app: {e}")
        print(f"Current sys.path: {sys.path}")
    except Exception as e:
        print(f"Error running server: {e}")

if __name__ == "__main__":
    print("=== WiFi-SPI Controller Startup Script ===")
    
    if is_admin():
        print("Status: Running with administrator privileges")
    else:
        print("Status: Running without administrator privileges")
        print("Requesting administrator privileges for firewall configuration...")
        restart_as_admin()
    
    if not install_requirements():
        print("Failed to setup environment.")
        input("Press Enter to exit...")
        sys.exit(1)
        
    config = load_config()
    print(f"Configuration loaded: {config}")

    port = config.get("port", 8000)
    setup_firewall(port)

    try:
        start_backend()
    except KeyboardInterrupt:
        print("\nStopping server...")
    except Exception as e:
        print(f"Error: {e}")
        input("Press Enter to exit...")
