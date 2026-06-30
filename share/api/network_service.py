# -*- coding: utf-8 -*-
import logging
import socket
import threading
import time
from typing import Optional, Callable

logger = logging.getLogger("network")


class NetworkService:
    """Client-mode network service with thread-safe socket access."""

    STATUS_DISCONNECTED = "disconnected"
    STATUS_CONNECTING = "connecting"
    STATUS_CONNECTED = "connected"
    STATUS_RECONNECTING = "reconnecting"

    RECONNECT_INITIAL_DELAY = 2.0
    RECONNECT_MAX_DELAY = 30.0
    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self):
        self._lock = threading.Lock()
        self.sock: Optional[socket.socket] = None
        self._status = self.STATUS_DISCONNECTED
        self.protocol: Optional[str] = None
        self.ip: Optional[str] = None
        self.port: Optional[int] = None
        self.on_receive: Optional[Callable[[bytes], None]] = None
        self.on_status_change: Optional[Callable[[str], None]] = None
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self._reconnect_thread: Optional[threading.Thread] = None
        self._reconnect_stop_event = threading.Event()
        self._reconnect_delay = self.RECONNECT_INITIAL_DELAY
        self._last_receive_time: float = 0.0
        self._user_initiated_disconnect = False
        self._reconnect_attempts: int = 0
        self._next_reconnect_time: Optional[float] = None

    @property
    def status(self) -> str:
        with self._lock:
            return self._status

    @property
    def connected(self) -> bool:
        with self._lock:
            return self._status == self.STATUS_CONNECTED

    @property
    def reconnect_attempts(self) -> int:
        with self._lock:
            return self._reconnect_attempts

    @property
    def next_reconnect_in(self) -> Optional[float]:
        with self._lock:
            if self._next_reconnect_time is None:
                return None
            remaining = self._next_reconnect_time - time.time()
            return max(0.0, remaining)

    def stop_reconnect(self):
        logger.info("Stop reconnect requested")
        self._user_initiated_disconnect = True
        self._stop_reconnect_thread()
        self._set_status(self.STATUS_DISCONNECTED)

    def _set_status(self, new_status: str):
        with self._lock:
            old_status = self._status
            self._status = new_status
        if old_status != new_status:
            logger.info(f"Network status changed: {old_status} -> {new_status}")
            if self.on_status_change:
                try:
                    self.on_status_change(new_status)
                except Exception as e:
                    logger.error(f"Status change callback error: {e}")

    def connect(self, ip: str, port: int, protocol: str) -> bool:
        self._stop_reconnect_thread()
        self._user_initiated_disconnect = False

        with self._lock:
            self._disconnect_internal()

        self.ip = ip
        self.port = port
        self.protocol = protocol.upper()

        self._set_status(self.STATUS_CONNECTING)

        try:
            sock = self._create_socket()
            with self._lock:
                self.sock = sock
                self.running = True
                self._last_receive_time = time.time()

            self._set_status(self.STATUS_CONNECTED)

            self.thread = threading.Thread(target=self._receive_loop, daemon=True)
            self.thread.start()
            logger.info(f"Network client connected: {self.protocol} {ip}:{port}")
            return True
        except socket.timeout:
            logger.warning(f"TCP connection timeout to {ip}:{port}")
            self._handle_connect_failure()
            return False
        except ConnectionRefusedError:
            logger.warning(f"Connection refused by {ip}:{port}")
            self._handle_connect_failure()
            return False
        except OSError as e:
            logger.error(f"Network connection OSError: {e}")
            self._handle_connect_failure()
            return False
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._handle_connect_failure()
            return False

    def _create_socket(self) -> socket.socket:
        if self.protocol == "UDP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect((self.ip, self.port))
        elif self.protocol == "TCP":
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5.0)
            sock.connect((self.ip, self.port))
        else:
            raise ValueError(f"Unsupported client protocol: {self.protocol}")
        return sock

    def _handle_connect_failure(self):
        if self.protocol == "TCP" and not self._user_initiated_disconnect:
            self._start_reconnect_thread()
        else:
            self._set_status(self.STATUS_DISCONNECTED)

    def disconnect(self):
        self._user_initiated_disconnect = True
        self._stop_reconnect_thread()

        with self._lock:
            was_connected = self._status == self.STATUS_CONNECTED
            self._disconnect_internal()

        if was_connected:
            logger.info("Network client disconnected")
        self._set_status(self.STATUS_DISCONNECTED)

    def _disconnect_internal(self):
        """Internal disconnect — must be called while holding self._lock."""
        self.running = False
        if self.sock:
            try:
                if self.protocol == "TCP":
                    self.sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None

    def send(self, data: bytes) -> bool:
        with self._lock:
            if not self.sock or self._status != self.STATUS_CONNECTED:
                logger.warning("Send skipped — not connected")
                return False

            sock = self.sock
            protocol = self.protocol

            try:
                if protocol == "UDP":
                    sock.send(data)
                else:
                    sock.sendall(data)
                logger.debug(f"Sent {len(data)} bytes via {protocol}")
                return True
            except (socket.timeout, BlockingIOError, InterruptedError) as e:
                logger.warning(f"Send transient error, retrying: {e}")
                try:
                    if protocol == "UDP":
                        sock.send(data)
                    else:
                        sock.sendall(data)
                    logger.debug(f"Sent {len(data)} bytes via {protocol} (retry)")
                    return True
                except Exception as e2:
                    logger.error(f"Send retry failed: {e2}")
                    self._disconnect_internal()
            except Exception as e:
                logger.error(f"Send error: {e}")
                self._disconnect_internal()

        self._on_connection_lost()
        return False

    def _on_connection_lost(self):
        if self.protocol == "TCP" and not self._user_initiated_disconnect:
            self._set_status(self.STATUS_DISCONNECTED)
            self._start_reconnect_thread()
        else:
            self._set_status(self.STATUS_DISCONNECTED)

    def _start_reconnect_thread(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            return
        self._reconnect_stop_event.clear()
        self._reconnect_delay = self.RECONNECT_INITIAL_DELAY
        self._reconnect_attempts = 0
        self._next_reconnect_time = time.time() + self._reconnect_delay
        self._set_status(self.STATUS_RECONNECTING)
        self._reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self._reconnect_thread.start()
        logger.info("Started TCP reconnect thread")

    def _stop_reconnect_thread(self):
        if self._reconnect_thread and self._reconnect_thread.is_alive():
            self._reconnect_stop_event.set()
            self._reconnect_thread.join(timeout=2.0)
            if self._reconnect_thread.is_alive():
                logger.warning("Reconnect thread did not stop cleanly")
            else:
                logger.info("Reconnect thread stopped")
        self._reconnect_thread = None

    def _reconnect_loop(self):
        while not self._reconnect_stop_event.is_set():
            logger.info(f"Attempting TCP reconnection in {self._reconnect_delay:.1f}s...")
            if self._reconnect_stop_event.wait(self._reconnect_delay):
                break

            if self._reconnect_stop_event.is_set():
                break

            self._reconnect_attempts += 1
            self._set_status(self.STATUS_CONNECTING)
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5.0)
                sock.connect((self.ip, self.port))

                with self._lock:
                    if self._reconnect_stop_event.is_set():
                        sock.close()
                        break
                    self.sock = sock
                    self.running = True
                    self._last_receive_time = time.time()

                self._set_status(self.STATUS_CONNECTED)
                self._reconnect_delay = self.RECONNECT_INITIAL_DELAY
                self._reconnect_attempts = 0
                self._next_reconnect_time = None
                self.thread = threading.Thread(target=self._receive_loop, daemon=True)
                self.thread.start()
                logger.info(f"TCP reconnected to {self.ip}:{self.port}")
                return
            except socket.timeout:
                logger.warning(f"TCP reconnect timeout to {self.ip}:{self.port}")
            except ConnectionRefusedError:
                logger.warning(f"TCP reconnect refused by {self.ip}:{self.port}")
            except OSError as e:
                logger.warning(f"TCP reconnect OSError: {e}")
            except Exception as e:
                logger.error(f"TCP reconnect error: {e}")

            self._reconnect_delay = min(self._reconnect_delay * 2, self.RECONNECT_MAX_DELAY)
            self._next_reconnect_time = time.time() + self._reconnect_delay
            self._set_status(self.STATUS_RECONNECTING)

        self._next_reconnect_time = None
        logger.info("Reconnect loop exiting")

    def _receive_loop(self):
        while self.running and self.sock:
            try:
                with self._lock:
                    if not self.sock:
                        break
                    sock = self.sock

                sock.settimeout(1.0)
                data = None
                try:
                    data = sock.recv(4096)
                except socket.timeout:
                    self._check_heartbeat_timeout()
                    continue
                except ConnectionResetError:
                    logger.warning("Connection reset by peer")
                    self._handle_receive_disconnect()
                    break
                except ConnectionAbortedError:
                    logger.warning("Connection aborted")
                    self._handle_receive_disconnect()
                    break

                if data:
                    with self._lock:
                        self._last_receive_time = time.time()
                    logger.debug(f"Received {len(data)} bytes from {self.ip}:{self.port}")
                    if self.on_receive:
                        self.on_receive(data)
                elif self.protocol == "TCP":
                    logger.info("TCP peer closed connection (empty recv)")
                    self._handle_receive_disconnect()
                    break
            except Exception as e:
                if self.running:
                    logger.error(f"Receive error: {e}")
                if self.protocol == "TCP":
                    self._handle_receive_disconnect()
                    break

    def _check_heartbeat_timeout(self):
        if self.protocol != "TCP":
            return
        with self._lock:
            elapsed = time.time() - self._last_receive_time
        if elapsed > self.HEARTBEAT_TIMEOUT:
            logger.warning(f"Heartbeat timeout: no data for {elapsed:.1f}s")
            self._handle_receive_disconnect()

    def _handle_receive_disconnect(self):
        with self._lock:
            self._disconnect_internal()
        self._on_connection_lost()


network_service = NetworkService()
