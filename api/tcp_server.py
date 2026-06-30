# -*- coding: utf-8 -*-
import logging
import socket
import threading
import time
import uuid
from typing import Optional, Callable, Dict, List, Any

logger = logging.getLogger("tcp_server")


class TCPServerService:
    """TCP server-mode service with thread-safe client management."""

    STATUS_STOPPED = "stopped"
    STATUS_RUNNING = "running"
    STATUS_ERROR = "error"

    HEARTBEAT_TIMEOUT = 60.0
    DEFAULT_MAX_CLIENTS = 8
    RECV_BUFFER_SIZE = 4096
    ACCEPT_TIMEOUT = 1.0

    def __init__(self):
        self._lock = threading.Lock()
        self._status = self.STATUS_STOPPED
        self._port: Optional[int] = None
        self._max_clients: int = self.DEFAULT_MAX_CLIENTS
        self.heartbeat_timeout: float = self.HEARTBEAT_TIMEOUT
        self._client_counter: int = 0
        self._clients: Dict[str, Dict[str, Any]] = {}
        self._server_sock: Optional[socket.socket] = None
        self._running = False
        self._accept_thread: Optional[threading.Thread] = None
        self._heartbeat_thread: Optional[threading.Thread] = None
        self._heartbeat_stop_event = threading.Event()

        self.on_client_connect: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_client_disconnect: Optional[Callable[[str, str], None]] = None
        self.on_receive: Optional[Callable[[str, bytes], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def port(self) -> Optional[int]:
        with self._lock:
            return self._port

    @property
    def max_clients(self) -> int:
        with self._lock:
            return self._max_clients

    @max_clients.setter
    def max_clients(self, value: int):
        with self._lock:
            self._max_clients = max(1, value)

    def _set_status(self, new_status: str):
        with self._lock:
            old_status = self._status
            self._status = new_status
        if old_status != new_status:
            logger.info(f"TCP server status changed: {old_status} -> {new_status}")
            if self.on_status_change:
                try:
                    self.on_status_change(new_status)
                except Exception as e:
                    logger.error(f"Status change callback error: {e}")

    def start(self, port: int, max_clients: Optional[int] = None, heartbeat_timeout: Optional[float] = None) -> bool:
        with self._lock:
            if self._status == self.STATUS_RUNNING:
                logger.warning("TCP server already running")
                return False
            if max_clients is not None:
                self._max_clients = max(1, max_clients)
            if heartbeat_timeout is not None:
                self.heartbeat_timeout = heartbeat_timeout

        self._port = port

        try:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_sock.bind(("0.0.0.0", port))
            server_sock.listen(self._max_clients)
            server_sock.settimeout(self.ACCEPT_TIMEOUT)

            with self._lock:
                self._server_sock = server_sock
                self._running = True
                self._clients.clear()

            self._set_status(self.STATUS_RUNNING)

            self._accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._accept_thread.start()

            self._heartbeat_stop_event.clear()
            self._heartbeat_thread = threading.Thread(target=self._heartbeat_check_loop, daemon=True)
            self._heartbeat_thread.start()

            logger.info(f"TCP server started on port {port}, max_clients={self._max_clients}")
            return True

        except OSError as e:
            logger.error(f"TCP server start OSError: {e}")
            self._cleanup_on_error()
            return False
        except Exception as e:
            logger.error(f"TCP server start error: {e}")
            self._cleanup_on_error()
            return False

    def _cleanup_on_error(self):
        with self._lock:
            if self._server_sock:
                try:
                    self._server_sock.close()
                except Exception:
                    pass
                self._server_sock = None
            self._running = False
            self._clients.clear()
        self._set_status(self.STATUS_ERROR)

    def stop(self):
        logger.info("TCP server stopping...")

        self._heartbeat_stop_event.set()
        self._heartbeat_thread = None

        with self._lock:
            self._running = False
            if self._server_sock:
                try:
                    self._server_sock.close()
                except Exception:
                    pass
                self._server_sock = None

            client_ids = list(self._clients.keys())

        for client_id in client_ids:
            self._disconnect_client(client_id, "server_stopped")

        self._accept_thread = None

        self._set_status(self.STATUS_STOPPED)
        logger.info("TCP server stopped")

    def _accept_loop(self):
        while self._running and self._server_sock:
            try:
                with self._lock:
                    if not self._server_sock or not self._running:
                        break
                    server_sock = self._server_sock

                try:
                    client_sock, addr = server_sock.accept()
                except socket.timeout:
                    continue

                ip, port = addr
                self._client_counter += 1
                client_id = str(self._client_counter)

                with self._lock:
                    if len(self._clients) >= self._max_clients:
                        logger.warning(f"Client {ip}:{port} rejected — max clients reached")
                        try:
                            client_sock.close()
                        except Exception:
                            pass
                        continue

                    now = time.time()
                    client_info = {
                        "client_id": client_id,
                        "ip": ip,
                        "port": port,
                        "connected_at": now,
                        "last_active": now,
                        "socket": client_sock,
                    }
                    self._clients[client_id] = client_info

                client_sock.settimeout(1.0)
                recv_thread = threading.Thread(
                    target=self._client_receive_loop,
                    args=(client_id,),
                    daemon=True,
                )
                recv_thread.start()

                logger.info(f"Client connected: {client_id} ({ip}:{port})")
                if self.on_client_connect:
                    try:
                        self.on_client_connect(self._get_client_public_info(client_id))
                    except Exception as e:
                        logger.error(f"Client connect callback error: {e}")

            except OSError as e:
                if self._running:
                    logger.error(f"Accept loop OSError: {e}")
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Accept loop error: {e}")

        logger.debug("Accept loop exiting")

    def _client_receive_loop(self, client_id: str):
        while self._running:
            with self._lock:
                client = self._clients.get(client_id)
                if not client:
                    break
                client_sock = client["socket"]

            try:
                data = client_sock.recv(self.RECV_BUFFER_SIZE)
            except socket.timeout:
                continue
            except ConnectionResetError:
                logger.info(f"Client {client_id} connection reset")
                self._disconnect_client(client_id, "connection_reset")
                break
            except ConnectionAbortedError:
                logger.info(f"Client {client_id} connection aborted")
                self._disconnect_client(client_id, "connection_aborted")
                break
            except OSError as e:
                logger.info(f"Client {client_id} recv OSError: {e}")
                self._disconnect_client(client_id, f"os_error:{e}")
                break
            except Exception as e:
                logger.error(f"Client {client_id} recv error: {e}")
                self._disconnect_client(client_id, f"error:{e}")
                break

            if data:
                with self._lock:
                    if client_id in self._clients:
                        self._clients[client_id]["last_active"] = time.time()
                logger.debug(f"Received {len(data)} bytes from {client_id}")
                if self.on_receive:
                    try:
                        self.on_receive(client_id, data)
                    except Exception as e:
                        logger.error(f"Receive callback error: {e}")
            else:
                logger.info(f"Client {client_id} closed connection (empty recv)")
                self._disconnect_client(client_id, "peer_closed")
                break

        logger.debug(f"Client receive loop exiting: {client_id}")

    def _disconnect_client(self, client_id: str, reason: str):
        with self._lock:
            client = self._clients.pop(client_id, None)

        if client:
            try:
                client["socket"].close()
            except Exception:
                pass
            logger.info(f"Client disconnected: {client_id}, reason={reason}")
            if self.on_client_disconnect:
                try:
                    self.on_client_disconnect(client_id, reason)
                except Exception as e:
                    logger.error(f"Client disconnect callback error: {e}")

    def _heartbeat_check_loop(self):
        while not self._heartbeat_stop_event.is_set():
            if self._heartbeat_stop_event.wait(5.0):
                break

            now = time.time()
            with self._lock:
                timeout_clients = [
                    cid
                    for cid, info in self._clients.items()
                    if now - info["last_active"] > self.heartbeat_timeout
                ]

            for client_id in timeout_clients:
                logger.warning(f"Client {client_id} heartbeat timeout")
                self._disconnect_client(client_id, "heartbeat_timeout")

        logger.debug("Heartbeat check loop exiting")

    def send_to_client(self, client_id: str, data: bytes) -> bool:
        with self._lock:
            client = self._clients.get(client_id)
            if not client:
                logger.warning(f"Send failed — client {client_id} not found")
                return False
            client_sock = client["socket"]

        try:
            client_sock.sendall(data)
            with self._lock:
                if client_id in self._clients:
                    self._clients[client_id]["last_active"] = time.time()
            logger.debug(f"Sent {len(data)} bytes to {client_id}")
            return True
        except (ConnectionResetError, BrokenPipeError) as e:
            logger.warning(f"Send to {client_id} failed: {e}")
            self._disconnect_client(client_id, f"send_error:{e}")
            return False
        except OSError as e:
            logger.warning(f"Send to {client_id} OSError: {e}")
            self._disconnect_client(client_id, f"send_error:{e}")
            return False
        except Exception as e:
            logger.error(f"Send to {client_id} error: {e}")
            self._disconnect_client(client_id, f"send_error:{e}")
            return False

    def send_to_all(self, data: bytes) -> int:
        success_count = 0
        with self._lock:
            client_ids = list(self._clients.keys())

        for client_id in client_ids:
            if self.send_to_client(client_id, data):
                success_count += 1

        logger.debug(f"Broadcast: {success_count}/{len(client_ids)} clients received {len(data)} bytes")
        return success_count

    def _get_client_public_info(self, client_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            client = self._clients.get(client_id)
            if not client:
                return None
            return {
                "client_id": client["client_id"],
                "ip": client["ip"],
                "port": client["port"],
                "connected_at": client["connected_at"],
                "last_active": client["last_active"],
            }

    def get_clients(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "client_id": info["client_id"],
                    "ip": info["ip"],
                    "port": info["port"],
                    "connected_at": info["connected_at"],
                    "last_active": info["last_active"],
                }
                for info in self._clients.values()
            ]

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self._status,
                "port": self._port,
                "max_clients": self._max_clients,
                "connected_clients": len(self._clients),
            }


tcp_server_service = TCPServerService()
