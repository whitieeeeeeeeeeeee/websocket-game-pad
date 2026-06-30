# -*- coding: utf-8 -*-
import sys
import os
import asyncio
import json
import logging
import time
import socket
import traceback
import urllib.request
from collections import deque
from datetime import datetime
from typing import List, Optional, Dict, Any

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler()],
)

logger = logging.getLogger("main")

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from controller import controller_manager
from network_service import network_service
from tcp_server import tcp_server_service
from recorder import recording_manager
from mock_service import mock_service

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")
HOST = "0.0.0.0"
PORT = 8000
controller_send_mode = 'onchange'  # default, may be overridden by config.json

try:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            HOST = config.get("host", HOST)
            PORT = config.get("port", PORT)
            controller_send_mode = config.get("controller_send_mode", controller_send_mode)
        logger.info(f"Loaded config from {CONFIG_FILE}")
    else:
        logger.info(f"Config file not found at {CONFIG_FILE}, using defaults")
except Exception as e:
    logger.error(f"Failed to load config.json: {e}, using defaults.")

APP_VERSION = "1.7.1"
APP_NAME = "WiFi-SPI Controller"

app = FastAPI(
    title="WiFi-SPI Controller API",
    description="WiFi-SPI 控制器后端服务",
    version=APP_VERSION
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def make_response(success: bool, message: str = "", **kwargs) -> Dict[str, Any]:
    response = {"success": success, "message": message}
    response.update(kwargs)
    return response


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.warning(f"HTTP {exc.status_code} at {request.url.path}: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content=make_response(False, str(exc.detail)),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception at {request.url.path}: {exc}")
    logger.debug(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content=make_response(False, "Internal server error"),
    )


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = datetime.now()
    response = await call_next(request)
    process_time = (datetime.now() - start_time).total_seconds() * 1000
    logger.debug(
        f"{request.method} {request.url.path} - {response.status_code} - {process_time:.1f}ms"
    )
    return response


class ConnectionRequest(BaseModel):
    ip: Optional[str] = None
    port: Optional[int] = None
    protocol: Optional[str] = None


class SendRequest(BaseModel):
    data: str
    format: str
    encoding: str = "utf-8"


class ServerStartRequest(BaseModel):
    port: int
    max_clients: int = 8
    heartbeat_timeout: Optional[int] = None


class ServerSendRequest(BaseModel):
    data: str
    format: str
    encoding: str = "utf-8"
    client_id: Optional[str] = None


class RecordingStartRequest(BaseModel):
    name: Optional[str] = None


class RecordingIdRequest(BaseModel):
    recording_id: str


class RecordingRenameRequest(BaseModel):
    recording_id: str
    new_name: str


class RecordingImportRequest(BaseModel):
    json_data: str


class PlaybackStartRequest(BaseModel):
    recording_id: str
    speed: float = 1.0


class PlaybackSeekRequest(BaseModel):
    progress: float


class PlaybackSpeedRequest(BaseModel):
    speed: float


class SetPlaybackModeRequest(BaseModel):
    enabled: bool
    block_real_controller: bool


class MockConnectRequest(BaseModel):
    name: Optional[str] = None


class MockStateRequest(BaseModel):
    buttons: Optional[Dict[str, bool]] = None
    axes: Optional[Dict[str, float]] = None
    triggers: Optional[Dict[str, float]] = None


class MockButtonPressRequest(BaseModel):
    button: str
    pressed: bool = True


class MockAxisMoveRequest(BaseModel):
    axis: str
    value: float


class MockNetworkReceiveRequest(BaseModel):
    data: str
    format: str = "hex"
    client_id: Optional[str] = None


class MockSystemLogRequest(BaseModel):
    level: str = "INFO"
    message: str
    module: str = "mock"


class FrequencyRequest(BaseModel):
    frequency: float


class SetSendModeRequest(BaseModel):
    mode: str  # 'continuous' or 'onchange'


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Browser WebSocket connected — {len(self.active_connections)} tabs active")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"Browser WebSocket disconnected — {len(self.active_connections)} tabs active")

    async def broadcast(self, message: dict):
        stale_connections: List[WebSocket] = []
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception:
                stale_connections.append(connection)
        for connection in stale_connections:
            self.disconnect(connection)


manager = ConnectionManager()
loop: Optional[asyncio.AbstractEventLoop] = None
log_buffer = deque(maxlen=100)
broadcast_interval = 0.05

instance_info = {
    "killed_old_instance": False,
    "kill_failed": False,
    "old_pid": None,
    "manual_kill_cmd": "",
}


def kill_old_instance(port=8000):
    """检测端口是否被占用，若被占用则尝试杀死旧实例"""
    global instance_info

    # 检测端口是否被占用
    test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    test_sock.settimeout(0.5)
    try:
        test_sock.bind(("0.0.0.0", port))
        test_sock.close()
        # 端口空闲，无需操作
        logger.info(f"Port {port} is free, starting new instance")
        return
    except OSError:
        test_sock.close()
        logger.info(f"Port {port} is in use, attempting to kill old instance...")

    # 尝试调用旧实例的 /api/shutdown
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/shutdown",
            method="POST",
            data=b"{}",
            headers={"Content-Type": "application/json"},
        )
        urllib.request.urlopen(req, timeout=3)
        logger.info("Shutdown request sent to old instance")
    except Exception as e:
        logger.warning(f"Failed to send shutdown request to old instance: {e}")

    # 等待端口释放（最多 5 秒，每 0.5 秒检测一次）
    port_released = False
    for _ in range(10):
        time.sleep(0.5)
        test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        test_sock.settimeout(0.5)
        try:
            test_sock.bind(("0.0.0.0", port))
            test_sock.close()
            port_released = True
            break
        except OSError:
            test_sock.close()

    if port_released:
        instance_info["killed_old_instance"] = True
        logger.info("Old instance killed successfully, port released")
    else:
        instance_info["kill_failed"] = True
        # 尝试获取占用端口的 PID（Windows）
        try:
            import subprocess
            result = subprocess.run(
                ["netstat", "-ano"],
                capture_output=True, text=True, timeout=3
            )
            for line in result.stdout.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        instance_info["old_pid"] = pid
                        instance_info["manual_kill_cmd"] = f"taskkill /F /PID {pid}"
                        break
        except Exception as e:
            logger.error(f"Failed to get PID: {e}")

        if not instance_info["manual_kill_cmd"]:
            instance_info["manual_kill_cmd"] = f"netstat -ano | findstr :{port}  # 然后用 taskkill /F /PID <pid> 杀死"

        logger.error(f"Failed to kill old instance. Manual kill command: {instance_info['manual_kill_cmd']}")


# Playback mode state - controls whether real controller data is sent to network
playback_mode_enabled = False
block_real_controller = True


class WebSocketLogHandler(logging.Handler):
    def __init__(self):
        super().__init__()
        self.setLevel(logging.INFO)

    def emit(self, record):
        try:
            log_entry = {
                "level": record.levelname,
                "module": record.name,
                "message": record.getMessage(),
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            }
            log_buffer.append(log_entry)

            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    manager.broadcast({
                        "type": "system_log",
                        "data": log_entry,
                    }),
                    loop,
                )
        except Exception:
            self.handleError(record)


def decode_bytes_for_log(data: bytes) -> str:
    for encoding in ("utf-8", "gb18030"):
        try:
            return data.decode(encoding)
        except Exception:
            continue
    return data.decode("latin-1", errors="replace")


def make_receive_log(data: bytes) -> dict:
    hex_data = data.hex().upper()
    text_data = decode_bytes_for_log(data)
    return {
        "direction": "receive",
        "timestamp": datetime.now().isoformat(),
        "data": hex_data,
        "text": text_data,
        "format": "hex",
    }


def make_send_log(req: SendRequest, auto: bool = False) -> dict:
    return {
        "direction": "send",
        "timestamp": datetime.now().isoformat(),
        "data": req.data,
        "text": req.data if req.format != "hex" else "",
        "format": req.format,
        "encoding": req.encoding,
        "auto": auto,
    }


def on_network_data(data: bytes):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "network_data",
                "data": make_receive_log(data),
            }),
            loop,
        )


def make_server_receive_log(client_id: str, data: bytes) -> dict:
    hex_data = data.hex().upper()
    text_data = decode_bytes_for_log(data)
    return {
        "client_id": client_id,
        "direction": "receive",
        "timestamp": datetime.now().isoformat(),
        "data": hex_data,
        "text": text_data,
        "format": "hex",
    }


def on_server_data(client_id: str, data: bytes):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "server_data",
                "data": make_server_receive_log(client_id, data),
            }),
            loop,
        )


def on_server_client_connect(client_info: dict):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "server_clients",
                "data": tcp_server_service.get_clients(),
            }),
            loop,
        )


def on_server_client_disconnect(client_id: str, reason: str):
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "server_clients",
                "data": tcp_server_service.get_clients(),
            }),
            loop,
        )


def on_server_status_change(status: str):
    if loop and loop.is_running():
        server_status = tcp_server_service.get_status()
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "server_status",
                "data": {
                    "status": server_status["status"],
                    "port": server_status["port"],
                    "client_count": server_status["connected_clients"],
                },
            }),
            loop,
        )


def on_recording_state_change(state: str):
    if loop and loop.is_running():
        recording_status = recording_manager.get_recording_status()
        playback_status = recording_manager.get_playback_status()
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "recording_state",
                "data": {
                    "state": state,
                    "recording": recording_status,
                    "playback": playback_status,
                },
            }),
            loop,
        )


def on_playback_frame(frame: dict):
    if loop and loop.is_running():
        playback_status = recording_manager.get_playback_status()
        broadcast_frame = {
            "buttons": frame.get("buttons", {}).copy(),
            "axes": frame.get("axes", {}).copy(),
            "triggers": frame.get("triggers", {}).copy(),
            "timestamp": frame.get("timestamp", 0),
            "connected": controller_manager.is_connected(),
            "is_playback": True,
            "playback_info": playback_status,
        }
        asyncio.run_coroutine_threadsafe(
            manager.broadcast({
                "type": "controller_state",
                "data": broadcast_frame,
            }),
            loop,
        )


@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    
    ws_handler = WebSocketLogHandler()
    ws_handler.setLevel(logging.INFO)
    root_logger = logging.getLogger()
    root_logger.addHandler(ws_handler)
    
    network_service.on_receive = on_network_data
    
    tcp_server_service.on_receive = on_server_data
    tcp_server_service.on_client_connect = on_server_client_connect
    tcp_server_service.on_client_disconnect = on_server_client_disconnect
    tcp_server_service.on_status_change = on_server_status_change
    
    recording_manager.on_state_change = on_recording_state_change
    recording_manager.on_frame = on_playback_frame
    
    controller_manager.start()
    asyncio.create_task(broadcast_controller_state())
    logger.info(f"Server started — http://{HOST}:{PORT}")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Server shutting down...")
    controller_manager.stop()
    network_service.disconnect()
    tcp_server_service.stop()
    logger.info("All services stopped")


async def graceful_shutdown():
    await asyncio.sleep(0.5)
    logger.info("Starting graceful shutdown sequence...")

    logger.info("Stopping controller_manager...")
    try:
        controller_manager.stop()
        logger.info("controller_manager stopped")
    except Exception as e:
        logger.error(f"Error stopping controller_manager: {e}")

    logger.info("Disconnecting network_service...")
    try:
        network_service.disconnect()
        logger.info("network_service disconnected")
    except Exception as e:
        logger.error(f"Error disconnecting network_service: {e}")

    logger.info("Stopping tcp_server_service...")
    try:
        tcp_server_service.stop()
        logger.info("tcp_server_service stopped")
    except Exception as e:
        logger.error(f"Error stopping tcp_server_service: {e}")

    logger.info("Closing all WebSocket connections...")
    try:
        for connection in list(manager.active_connections):
            try:
                await connection.close()
            except Exception:
                pass
        manager.active_connections.clear()
        logger.info("All WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket connections: {e}")

    logger.info("Shutdown complete, exiting process...")
    os._exit(0)


@app.get("/api/version")
async def get_version():
    return {
        "version": APP_VERSION,
        "name": APP_NAME
    }


@app.post("/api/shutdown")
async def shutdown():
    logger.info("Shutdown requested via API")
    asyncio.create_task(graceful_shutdown())
    return make_response(True, "Shutting down...")


@app.get("/api/instance/info")
async def get_instance_info():
    return make_response(True, "Instance info", **instance_info)


@app.get("/api/controller/status")
async def get_controller_status():
    real_state = controller_manager.get_state()
    real_state["timestamp"] = real_state["timestamp"].isoformat()
    real_state["connected"] = controller_manager.is_connected()
    
    use_mock = mock_service.mock_enabled and mock_service.is_connected()
    
    if use_mock:
        mock_state = mock_service.get_state()
        mock_state["timestamp"] = mock_state["timestamp"].isoformat()
        return {
            "buttons": mock_state["buttons"],
            "axes": mock_state["axes"],
            "triggers": mock_state["triggers"],
            "timestamp": mock_state["timestamp"],
            "connected": mock_state["connected"],
            "device_info": mock_state["device_info"],
            "is_mock": True,
            "real_connected": real_state["connected"],
        }
    else:
        return {
            "buttons": real_state["buttons"],
            "axes": real_state["axes"],
            "triggers": real_state["triggers"],
            "timestamp": real_state["timestamp"],
            "connected": real_state["connected"],
            "device_info": real_state["device_info"],
            "is_mock": False,
        }


@app.post("/api/controller/detect")
async def detect_controller():
    logger.info("Controller detect requested via API")
    success, message = controller_manager.force_detect()
    return make_response(success, message)


@app.get("/api/controller/frequency")
async def get_controller_frequency():
    frequency = 1.0 / broadcast_interval
    return make_response(True, frequency=frequency)


@app.post("/api/controller/frequency")
async def set_controller_frequency(req: FrequencyRequest):
    global broadcast_interval
    if req.frequency < 10 or req.frequency > 60:
        raise HTTPException(status_code=400, detail="Frequency must be between 10 and 60 Hz")
    broadcast_interval = 1.0 / req.frequency
    logger.info(f"Controller broadcast frequency set to {req.frequency} Hz (interval={broadcast_interval:.4f}s)")
    return make_response(True, "Frequency updated", frequency=req.frequency)


@app.get("/api/controller/send-mode")
async def get_controller_send_mode():
    return make_response(True, mode=controller_send_mode)


@app.post("/api/controller/send-mode")
async def set_controller_send_mode(req: SetSendModeRequest):
    global controller_send_mode
    if req.mode not in ('continuous', 'onchange'):
        raise HTTPException(status_code=400, detail="Mode must be 'continuous' or 'onchange'")
    controller_send_mode = req.mode
    logger.info(f"Controller send mode set to: {controller_send_mode}")
    # 持久化到 config.json
    try:
        existing_config = {}
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                existing_config = json.load(f)
        existing_config["controller_send_mode"] = controller_send_mode
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to persist controller_send_mode: {e}")
    return make_response(True, "Send mode updated", mode=controller_send_mode)


async def broadcast_controller_state():
    while True:
        if manager.active_connections:
            real_state = controller_manager.get_state()
            real_state["timestamp"] = real_state["timestamp"].isoformat()

            use_mock = mock_service.mock_enabled and mock_service.is_connected()

            if use_mock:
                mock_state = mock_service.get_state()
                mock_state["timestamp"] = mock_state["timestamp"].isoformat()
                state = {
                    "buttons": mock_state["buttons"],
                    "axes": mock_state["axes"],
                    "triggers": mock_state["triggers"],
                    "timestamp": mock_state["timestamp"],
                    "connected": mock_state["connected"],
                    "device_info": mock_state["device_info"],
                    "is_mock": True,
                    "real_connected": real_state["connected"],
                }
            else:
                state = {
                    "buttons": real_state["buttons"],
                    "axes": real_state["axes"],
                    "triggers": real_state["triggers"],
                    "timestamp": real_state["timestamp"],
                    "connected": real_state["connected"],
                    "device_info": real_state["device_info"],
                    "is_mock": False,
                }

            if recording_manager.get_state() == recording_manager.STATE_RECORDING:
                recording_manager.add_frame(state)

            playback_frame = recording_manager.get_current_frame()
            playback_state = recording_manager.get_playback_status()
            is_playback_active = playback_state["state"] in (
                recording_manager.STATE_PLAYING,
                recording_manager.STATE_PLAYBACK_PAUSED,
            )

            if is_playback_active and playback_frame:
                broadcast_state = {
                    "buttons": playback_frame["buttons"].copy(),
                    "axes": playback_frame["axes"].copy(),
                    "triggers": playback_frame["triggers"].copy(),
                    "timestamp": playback_frame["timestamp"],
                    "connected": state["connected"],
                    "device_info": state["device_info"],
                    "is_playback": True,
                    "playback_info": playback_state,
                    "is_mock": state.get("is_mock", False),
                }
            else:
                broadcast_state = {
                    "buttons": state["buttons"].copy(),
                    "axes": state["axes"].copy(),
                    "triggers": state["triggers"].copy(),
                    "timestamp": state["timestamp"],
                    "connected": state["connected"],
                    "device_info": state["device_info"],
                    "is_mock": state["is_mock"],
                    "is_playback": False,
                }
                if use_mock:
                    broadcast_state["real_connected"] = state["real_connected"]

            await manager.broadcast({
                "type": "controller_state",
                "data": broadcast_state,
            })

            # Check if we should send real controller data
            # Skip if: playback mode enabled AND block real controller AND this is real controller data (not playback)
            should_send_real = not (playback_mode_enabled and block_real_controller and not broadcast_state.get("is_playback", False))

            # 检测状态是否变化
            if not hasattr(broadcast_controller_state, '_last_sent_state'):
                broadcast_controller_state._last_sent_state = None

            current_snapshot = (
                tuple(broadcast_state["buttons"].items()),
                tuple(broadcast_state["axes"].items()),
                tuple(broadcast_state["triggers"].items()),
            )

            state_changed = (broadcast_controller_state._last_sent_state != current_snapshot)
            broadcast_controller_state._last_sent_state = current_snapshot

            # 发送模式：
            # - 'continuous': 始终按频率发送
            # - 'onchange': 状态变化时发送；持续按住按键/推动摇杆时也持续按频率发送
            #   （按键按下、扳机非零、摇杆偏离中心都视为"活跃输入"）
            has_active_input = (
                any(broadcast_state["buttons"].values())
                or any(abs(v) > 0.01 for v in broadcast_state["axes"].values())
                or any(v > 0.01 for v in broadcast_state["triggers"].values())
            )
            should_send = (controller_send_mode == 'continuous') or state_changed or has_active_input

            # auto-log 节流
            if not hasattr(broadcast_controller_state, '_last_auto_log_time'):
                broadcast_controller_state._last_auto_log_time = 0.0

            now_ts = time.time()
            should_log = (now_ts - broadcast_controller_state._last_auto_log_time) >= 0.2
            if should_log:
                broadcast_controller_state._last_auto_log_time = now_ts

            if state["connected"] and network_service.connected and should_send_real and should_send:
                try:
                    simple_state = {
                        "btns": broadcast_state["buttons"].copy(),
                        "axes": broadcast_state["axes"].copy(),
                        "trigs": broadcast_state["triggers"].copy(),
                    }
                    data_str = json.dumps(simple_state)
                    network_service.send(data_str.encode("utf-8"))
                    if should_log:
                        auto_log = {
                            "direction": "send",
                            "timestamp": datetime.now().isoformat(),
                            "data": data_str,
                            "text": data_str,
                            "format": "text",
                            "encoding": "utf-8",
                            "auto": True,
                        }
                        await manager.broadcast({
                            "type": "network_data",
                            "data": auto_log,
                        })
                except Exception as e:
                    logger.error(f"Auto-send error: {e}")

            if tcp_server_service.status == tcp_server_service.STATUS_RUNNING and should_send_real and should_send:
                try:
                    simple_state = {
                        "btns": broadcast_state["buttons"].copy(),
                        "axes": broadcast_state["axes"].copy(),
                        "trigs": broadcast_state["triggers"].copy(),
                    }
                    data_str = json.dumps(simple_state)
                    tcp_server_service.send_to_all(data_str.encode("utf-8"))
                    if should_log:
                        auto_log = {
                            "direction": "send",
                            "timestamp": datetime.now().isoformat(),
                            "data": data_str,
                            "text": data_str,
                            "format": "text",
                            "encoding": "utf-8",
                            "auto": True,
                        }
                        await manager.broadcast({
                            "type": "server_data",
                            "data": auto_log,
                        })
                except Exception as e:
                    logger.error(f"TCP server broadcast error: {e}")

            if recording_manager.get_state() in (
                recording_manager.STATE_RECORDING,
                recording_manager.STATE_PAUSED,
                recording_manager.STATE_PLAYING,
                recording_manager.STATE_PLAYBACK_PAUSED,
            ):
                try:
                    recording_status = recording_manager.get_recording_status()
                    playback_status = recording_manager.get_playback_status()
                    await manager.broadcast({
                        "type": "recording_state",
                        "data": {
                            "recording": recording_status,
                            "playback": playback_status,
                        },
                    })
                except Exception as e:
                    logger.error(f"Recording state broadcast error: {e}")

        await asyncio.sleep(broadcast_interval)


@app.post("/api/network/connect")
async def connect_network(req: ConnectionRequest):
    logger.info(f"Connect request: {req.protocol} {req.ip}:{req.port}")
    
    if not req.ip or not req.port or not req.protocol:
        logger.warning("Connect request missing required parameters")
        return make_response(False, "Missing ip, port, or protocol")
    
    try:
        success = network_service.connect(req.ip, req.port, req.protocol)
        if success:
            logger.info(f"Successfully connected to {req.protocol} {req.ip}:{req.port}")
        else:
            logger.warning(f"Failed to connect to {req.protocol} {req.ip}:{req.port}")
        
        return make_response(
            success,
            "Connected" if success else "Connection failed",
            status=success,
            ip=req.ip,
            port=req.port,
            protocol=req.protocol.upper(),
        )
    except Exception as e:
        logger.error(f"Connect error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Connection error: {str(e)}")


@app.post("/api/network/disconnect")
async def disconnect_network():
    logger.info("Disconnect requested via API")
    try:
        network_service.disconnect()
        logger.info("Network disconnected successfully")
        return make_response(True, "Disconnected")
    except Exception as e:
        logger.error(f"Disconnect error: {e}")
        return make_response(False, f"Disconnect error: {str(e)}")


@app.post("/api/network/status")
async def get_network_status():
    logger.debug(f"Status request - status: {network_service.status}")
    result = {
        "connected": network_service.connected,
        "ip": network_service.ip,
        "port": network_service.port,
        "protocol": network_service.protocol,
        "status": network_service.status,
    }
    if network_service.status == network_service.STATUS_RECONNECTING:
        result["reconnect_attempts"] = network_service.reconnect_attempts
        result["next_reconnect_in"] = network_service.next_reconnect_in
    else:
        result["reconnect_attempts"] = 0
        result["next_reconnect_in"] = None
    return result


@app.post("/api/network/stop-reconnect")
async def stop_reconnect():
    logger.info("Stop reconnect request via API")
    try:
        network_service.stop_reconnect()
        logger.info("Reconnect stopped successfully")
        return make_response(True, "Reconnect stopped")
    except Exception as e:
        logger.error(f"Stop reconnect error: {e}")
        return make_response(False, f"Stop reconnect error: {str(e)}")


@app.post("/api/network/send")
async def send_data(req: SendRequest):
    logger.debug(f"Send request - format: {req.format}, encoding: {req.encoding}, length: {len(req.data)}")
    
    try:
        if req.format == "hex":
            clean_data = req.data.replace(" ", "")
            try:
                data_bytes = bytes.fromhex(clean_data)
            except ValueError as e:
                logger.warning(f"Invalid hex data: {e}")
                return make_response(False, f"Invalid hex format: {str(e)}", bytes_sent=0)
        else:
            try:
                data_bytes = req.data.encode(req.encoding)
            except LookupError as e:
                logger.warning(f"Unknown encoding '{req.encoding}', falling back to utf-8: {e}")
                data_bytes = req.data.encode("utf-8")
            except Exception as e:
                logger.warning(f"Encoding error ({req.encoding}): {e}, falling back to utf-8")
                data_bytes = req.data.encode("utf-8")

        success = network_service.send(data_bytes)
        if success:
            logger.info(f"Sent {len(data_bytes)} bytes via {network_service.protocol}")
        elif tcp_server_service.status == tcp_server_service.STATUS_RUNNING:
            # TCP server 模式：通过 tcp_server_service 发送
            sent_count = tcp_server_service.send_to_all(data_bytes)
            success = sent_count > 0
            if success:
                logger.info(f"Sent {len(data_bytes)} bytes to {sent_count} TCP client(s)")
            else:
                logger.warning("Send failed - no TCP clients connected")
        else:
            logger.warning("Send failed - not connected or send error")

        if success:
            await manager.broadcast({
                "type": "network_data",
                "data": make_send_log(req),
            })

        return make_response(
            success,
            "Sent successfully" if success else "Send failed",
            bytes_sent=len(data_bytes) if success else 0,
        )
    except Exception as e:
        logger.error(f"Send data error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Send error: {str(e)}", bytes_sent=0)


@app.post("/api/server/start")
async def start_server(req: ServerStartRequest):
    logger.info(f"Server start request - port: {req.port}, max_clients: {req.max_clients}")
    try:
        success = tcp_server_service.start(port=req.port, max_clients=req.max_clients, heartbeat_timeout=req.heartbeat_timeout)
        if success:
            logger.info(f"TCP server started on port {req.port}")
        else:
            logger.warning(f"Failed to start TCP server on port {req.port}")
        status = tcp_server_service.get_status()
        return make_response(
            success,
            "Server started" if success else "Server start failed",
            status=status["status"],
            port=status["port"],
        )
    except Exception as e:
        logger.error(f"Server start error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Server start error: {str(e)}")


@app.post("/api/server/stop")
async def stop_server():
    logger.info("Server stop request via API")
    try:
        tcp_server_service.stop()
        logger.info("TCP server stopped")
        return make_response(True, "Server stopped")
    except Exception as e:
        logger.error(f"Server stop error: {e}")
        return make_response(False, f"Server stop error: {str(e)}")


@app.post("/api/server/status")
async def get_server_status():
    logger.debug(f"Server status request")
    status = tcp_server_service.get_status()
    return {
        "status": status["status"],
        "port": status["port"],
        "client_count": status["connected_clients"],
    }


@app.post("/api/server/clients")
async def get_server_clients():
    logger.debug("Server clients request")
    try:
        clients = tcp_server_service.get_clients()
        return make_response(True, clients=clients)
    except Exception as e:
        logger.error(f"Get server clients error: {e}")
        return make_response(False, f"Get clients error: {str(e)}", clients=[])


@app.post("/api/server/info")
async def get_server_info():
    """返回服务端信息：本机所有 IPv4 地址、监听端口、运行状态"""
    import socket
    ips = []
    try:
        hostname = socket.gethostname()
        addrinfo = socket.getaddrinfo(hostname, None, socket.AF_INET)
        for item in addrinfo:
            ip = item[4][0]
            if ip != '127.0.0.1' and ip not in ips:
                ips.append(ip)
    except Exception as e:
        logger.debug(f"Get local IP error: {e}")
    status = tcp_server_service.get_status()
    return {
        "ips": ips,
        "port": status["port"],
        "status": status["status"],
        "client_count": status["connected_clients"],
    }


@app.post("/api/server/send")
async def send_server_data(req: ServerSendRequest):
    logger.debug(f"Server send request - format: {req.format}, encoding: {req.encoding}, client_id: {req.client_id}")
    
    try:
        if req.format == "hex":
            clean_data = req.data.replace(" ", "")
            try:
                data_bytes = bytes.fromhex(clean_data)
            except ValueError as e:
                logger.warning(f"Invalid hex data: {e}")
                return make_response(False, f"Invalid hex format: {str(e)}", bytes_sent=0)
        else:
            try:
                data_bytes = req.data.encode(req.encoding)
            except LookupError as e:
                logger.warning(f"Unknown encoding '{req.encoding}', falling back to utf-8: {e}")
                data_bytes = req.data.encode("utf-8")
            except Exception as e:
                logger.warning(f"Encoding error ({req.encoding}): {e}, falling back to utf-8")
                data_bytes = req.data.encode("utf-8")

        if req.client_id:
            success = tcp_server_service.send_to_client(req.client_id, data_bytes)
            bytes_sent = len(data_bytes) if success else 0
            if success:
                logger.info(f"Sent {len(data_bytes)} bytes to client {req.client_id}")
            else:
                logger.warning(f"Send to client {req.client_id} failed")
        else:
            count = tcp_server_service.send_to_all(data_bytes)
            bytes_sent = len(data_bytes) * count
            logger.info(f"Broadcast {len(data_bytes)} bytes to {count} clients")
            success = count > 0

        return make_response(
            success,
            "Sent successfully" if success else "Send failed",
            bytes_sent=bytes_sent,
        )
    except Exception as e:
        logger.error(f"Server send data error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Send error: {str(e)}", bytes_sent=0)


@app.post("/api/recording/start")
async def start_recording(req: RecordingStartRequest):
    logger.info(f"Recording start request - name: {req.name}")
    try:
        success = recording_manager.start_recording(req.name)
        if success:
            status = recording_manager.get_recording_status()
            logger.info(f"Recording started: {status['name']}")
        else:
            logger.warning("Failed to start recording")
        return make_response(
            success,
            "Recording started" if success else "Failed to start recording",
            status=recording_manager.get_recording_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Start recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Start recording error: {str(e)}")


@app.post("/api/recording/pause")
async def pause_recording():
    logger.info("Recording pause request")
    try:
        success = recording_manager.pause_recording()
        if success:
            logger.info("Recording paused")
        else:
            logger.warning("Failed to pause recording")
        return make_response(
            success,
            "Recording paused" if success else "Failed to pause recording",
            status=recording_manager.get_recording_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Pause recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Pause recording error: {str(e)}")


@app.post("/api/recording/resume")
async def resume_recording():
    logger.info("Recording resume request")
    try:
        success = recording_manager.resume_recording()
        if success:
            status = recording_manager.get_recording_status()
            logger.info("Recording resumed")
            return make_response(True, "Recording resumed", status=status)
        else:
            logger.warning("Failed to resume recording")
            return make_response(False, "Failed to resume recording")
    except Exception as e:
        logger.error(f"Resume recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Resume recording error: {str(e)}")


@app.post("/api/recording/stop")
async def stop_recording():
    logger.info("Recording stop request")
    try:
        recording = recording_manager.stop_recording()
        success = recording is not None
        if success:
            logger.info(f"Recording stopped: {recording['name']}")
        else:
            logger.warning("Failed to stop recording")
        return make_response(
            success,
            "Recording stopped" if success else "Failed to stop recording",
            recording=recording if success else None,
        )
    except Exception as e:
        logger.error(f"Stop recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Stop recording error: {str(e)}")


@app.post("/api/recording/list")
async def list_recordings():
    logger.debug("Recording list request")
    try:
        recordings = recording_manager.list_recordings()
        return make_response(True, recordings=recordings)
    except Exception as e:
        logger.error(f"List recordings error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"List recordings error: {str(e)}", recordings=[])


@app.post("/api/recording/get")
async def get_recording(req: RecordingIdRequest):
    logger.debug(f"Recording get request - id: {req.recording_id}")
    try:
        recording = recording_manager.get_recording(req.recording_id)
        if recording:
            return make_response(True, recording=recording)
        else:
            logger.warning(f"Recording not found: {req.recording_id}")
            return make_response(False, "Recording not found", recording=None)
    except Exception as e:
        logger.error(f"Get recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Get recording error: {str(e)}", recording=None)


@app.post("/api/recording/rename")
async def rename_recording(req: RecordingRenameRequest):
    logger.info(f"Recording rename request - id: {req.recording_id}, new_name: {req.new_name}")
    try:
        success = recording_manager.rename_recording(req.recording_id, req.new_name)
        if success:
            logger.info(f"Recording renamed to: {req.new_name}")
        else:
            logger.warning(f"Failed to rename recording: {req.recording_id}")
        return make_response(
            success,
            "Recording renamed" if success else "Failed to rename recording",
        )
    except Exception as e:
        logger.error(f"Rename recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Rename recording error: {str(e)}")


@app.post("/api/recording/delete")
async def delete_recording(req: RecordingIdRequest):
    logger.info(f"Recording delete request - id: {req.recording_id}")
    try:
        success = recording_manager.delete_recording(req.recording_id)
        if success:
            logger.info(f"Recording deleted: {req.recording_id}")
        else:
            logger.warning(f"Failed to delete recording: {req.recording_id}")
        return make_response(
            success,
            "Recording deleted" if success else "Failed to delete recording",
        )
    except Exception as e:
        logger.error(f"Delete recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Delete recording error: {str(e)}")


@app.post("/api/recording/export")
async def export_recording(req: RecordingIdRequest):
    logger.info(f"Recording export request - id: {req.recording_id}")
    try:
        json_data = recording_manager.export_recording(req.recording_id)
        if json_data:
            logger.info(f"Recording exported: {req.recording_id}")
            return make_response(True, "Recording exported", json_data=json_data)
        else:
            logger.warning(f"Failed to export recording: {req.recording_id}")
            return make_response(False, "Failed to export recording", json_data=None)
    except Exception as e:
        logger.error(f"Export recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Export recording error: {str(e)}", json_data=None)


@app.post("/api/recording/import")
async def import_recording(req: RecordingImportRequest):
    logger.info(f"Recording import request - data length: {len(req.json_data)}")
    try:
        recording = recording_manager.import_recording(req.json_data)
        if recording:
            logger.info(f"Recording imported: {recording['name']}")
            return make_response(True, "Recording imported", recording=recording)
        else:
            logger.warning("Failed to import recording")
            return make_response(False, "Failed to import recording", recording=None)
    except Exception as e:
        logger.error(f"Import recording error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Import recording error: {str(e)}", recording=None)


@app.post("/api/playback/start")
async def start_playback(req: PlaybackStartRequest):
    logger.info(f"Playback start request - recording_id: {req.recording_id}, speed: {req.speed}")
    try:
        success = recording_manager.start_playback(req.recording_id, req.speed)
        if success:
            status = recording_manager.get_playback_status()
            logger.info(f"Playback started: {status['recording_name']}")
        else:
            logger.warning("Failed to start playback")
        return make_response(
            success,
            "Playback started" if success else "Failed to start playback",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Start playback error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Start playback error: {str(e)}")


@app.post("/api/playback/pause")
async def pause_playback():
    logger.info("Playback pause request")
    try:
        success = recording_manager.pause_playback()
        if success:
            logger.info("Playback paused")
        else:
            logger.warning("Failed to pause playback")
        return make_response(
            success,
            "Playback paused" if success else "Failed to pause playback",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Pause playback error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Pause playback error: {str(e)}")


@app.post("/api/playback/resume")
async def resume_playback():
    logger.info("Playback resume request")
    try:
        success = recording_manager.resume_playback()
        if success:
            logger.info("Playback resumed")
        else:
            logger.warning("Failed to resume playback")
        return make_response(
            success,
            "Playback resumed" if success else "Failed to resume playback",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Resume playback error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Resume playback error: {str(e)}")


@app.post("/api/playback/stop")
async def stop_playback():
    logger.info("Playback stop request")
    try:
        success = recording_manager.stop_playback()
        if success:
            logger.info("Playback stopped")
        else:
            logger.warning("Failed to stop playback")
        return make_response(
            success,
            "Playback stopped" if success else "Failed to stop playback",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Stop playback error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Stop playback error: {str(e)}")


@app.post("/api/playback/seek")
async def seek_playback(req: PlaybackSeekRequest):
    logger.info(f"Playback seek request - progress: {req.progress}")
    try:
        success = recording_manager.seek_playback(req.progress)
        if success:
            logger.info(f"Playback seeked to {req.progress*100:.1f}%")
        else:
            logger.warning("Failed to seek playback")
        return make_response(
            success,
            "Playback seeked" if success else "Failed to seek playback",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Seek playback error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Seek playback error: {str(e)}")


@app.post("/api/playback/speed")
async def set_playback_speed(req: PlaybackSpeedRequest):
    logger.info(f"Playback speed request - speed: {req.speed}")
    try:
        success = recording_manager.set_playback_speed(req.speed)
        if success:
            logger.info(f"Playback speed set to {req.speed}x")
        else:
            logger.warning("Failed to set playback speed")
        return make_response(
            success,
            "Playback speed set" if success else "Failed to set playback speed",
            status=recording_manager.get_playback_status() if success else None,
        )
    except Exception as e:
        logger.error(f"Set playback speed error: {e}")
        logger.debug(traceback.format_exc())
        return make_response(False, f"Set playback speed error: {str(e)}")


@app.post("/api/playback/mode")
async def set_playback_mode(req: SetPlaybackModeRequest):
    global playback_mode_enabled, block_real_controller
    logger.info(f"Set playback mode - enabled: {req.enabled}, block_real: {req.block_real_controller}")
    try:
        playback_mode_enabled = req.enabled
        block_real_controller = req.block_real_controller
        logger.info(f"Playback mode updated - enabled={playback_mode_enabled}, block_real={block_real_controller}")
        return make_response(True, "Playback mode set successfully")
    except Exception as e:
        logger.error(f"Set playback mode error: {e}")
        return make_response(False, f"Set playback mode error: {str(e)}")


@app.get("/api/mock/status")
async def get_mock_status():
    mock_state = mock_service.get_state()
    mock_state["timestamp"] = mock_state["timestamp"].isoformat()
    return make_response(
        True,
        mock_enabled=mock_service.mock_enabled,
        controller_connected=mock_service.is_connected(),
        device_info=mock_state["device_info"],
        buttons=mock_state["buttons"],
        axes=mock_state["axes"],
        triggers=mock_state["triggers"],
    )


@app.post("/api/mock/controller/connect")
async def mock_connect_controller(req: MockConnectRequest):
    logger.info(f"Mock connect request - name: {req.name}")
    try:
        success = mock_service.connect_controller(req.name)
        return make_response(
            success,
            "Mock controller connected" if success else "Failed to connect mock controller",
        )
    except Exception as e:
        logger.error(f"Mock connect error: {e}")
        return make_response(False, f"Mock connect error: {str(e)}")


@app.post("/api/mock/controller/disconnect")
async def mock_disconnect_controller():
    logger.info("Mock disconnect request")
    try:
        success = mock_service.disconnect_controller()
        return make_response(
            success,
            "Mock controller disconnected" if success else "Failed to disconnect mock controller",
        )
    except Exception as e:
        logger.error(f"Mock disconnect error: {e}")
        return make_response(False, f"Mock disconnect error: {str(e)}")


@app.post("/api/mock/controller/state")
async def mock_set_state(req: MockStateRequest):
    logger.debug(f"Mock set state request")
    try:
        success = mock_service.set_state(req.buttons, req.axes, req.triggers)
        return make_response(
            success,
            "State updated" if success else "Failed to update state",
        )
    except Exception as e:
        logger.error(f"Mock set state error: {e}")
        return make_response(False, f"Mock set state error: {str(e)}")


@app.post("/api/mock/controller/button-press")
async def mock_button_press(req: MockButtonPressRequest):
    logger.debug(f"Mock button press - button: {req.button}, pressed: {req.pressed}")
    try:
        success = mock_service.press_button(req.button, req.pressed)
        return make_response(
            success,
            f"Button {req.button} {'pressed' if req.pressed else 'released'}" if success else f"Unknown button: {req.button}",
        )
    except Exception as e:
        logger.error(f"Mock button press error: {e}")
        return make_response(False, f"Mock button press error: {str(e)}")


@app.post("/api/mock/controller/axis-move")
async def mock_axis_move(req: MockAxisMoveRequest):
    logger.debug(f"Mock axis move - axis: {req.axis}, value: {req.value}")
    try:
        success = mock_service.move_axis(req.axis, req.value)
        return make_response(
            success,
            f"Axis {req.axis} moved" if success else f"Unknown axis: {req.axis}",
        )
    except Exception as e:
        logger.error(f"Mock axis move error: {e}")
        return make_response(False, f"Mock axis move error: {str(e)}")


@app.post("/api/mock/network/receive")
async def mock_network_receive(req: MockNetworkReceiveRequest):
    logger.info(f"Mock network receive - format: {req.format}, client_id: {req.client_id}")
    try:
        if req.format == "hex":
            clean_data = req.data.replace(" ", "")
            try:
                data_bytes = bytes.fromhex(clean_data)
            except ValueError as e:
                logger.warning(f"Invalid hex data: {e}")
                return make_response(False, f"Invalid hex format: {str(e)}")
        else:
            data_bytes = req.data.encode("utf-8")

        if req.client_id:
            log_entry = make_server_receive_log(req.client_id, data_bytes)
            await manager.broadcast({
                "type": "server_data",
                "data": log_entry,
            })
        else:
            log_entry = make_receive_log(data_bytes)
            await manager.broadcast({
                "type": "network_data",
                "data": log_entry,
            })

        return make_response(True, "Mock data received and broadcasted")
    except Exception as e:
        logger.error(f"Mock network receive error: {e}")
        return make_response(False, f"Mock network receive error: {str(e)}")


@app.post("/api/mock/system/log")
async def mock_system_log(req: MockSystemLogRequest):
    logger.debug(f"Mock system log - level: {req.level}, module: {req.module}")
    try:
        log_entry = {
            "level": req.level.upper(),
            "module": req.module,
            "message": req.message,
            "timestamp": datetime.now().isoformat(),
        }
        log_buffer.append(log_entry)
        await manager.broadcast({
            "type": "system_log",
            "data": log_entry,
        })
        return make_response(True, "Mock log broadcasted")
    except Exception as e:
        logger.error(f"Mock system log error: {e}")
        return make_response(False, f"Mock system log error: {str(e)}")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        if log_buffer:
            await websocket.send_json({
                "type": "system_log_history",
                "data": list(log_buffer),
            })
        
        recording_status = recording_manager.get_recording_status()
        playback_status = recording_manager.get_playback_status()
        await websocket.send_json({
            "type": "recording_state",
            "data": {
                "state": recording_manager.get_state(),
                "recording": recording_status,
                "playback": playback_status,
            },
        })
        
        while True:
            try:
                data = await websocket.receive_text()
                logger.debug(f"Browser WS received text: {data[:100]}")
            except WebSocketDisconnect:
                break
    except Exception as e:
        logger.error(f"Browser WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


dist_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "dist")
if os.path.exists(dist_path):
    app.mount("/", StaticFiles(directory=dist_path, html=True), name="static")


if __name__ == "__main__":
    kill_old_instance(PORT)
    uvicorn.run(app, host=HOST, port=PORT)
