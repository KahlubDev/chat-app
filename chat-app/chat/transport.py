"""Transport layer: creates sockets, sends data and receives data.

This layer knows nothing about JSON or chat rules.
It moves lines of text over TCP. One line ends with a newline character.
"""
import socket
import threading

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 5000
ENCODING = "utf-8"
MAX_LINE_BYTES = 65536


class TransportError(Exception):
    """Raised when a socket operation fails."""


class Connection:
    """One TCP connection. Sends and receives newline-terminated text lines."""

    def __init__(self, sock):
        self._sock = sock
        self._buffer = b""
        self._send_lock = threading.Lock()

    def set_timeout(self, seconds):
        self._sock.settimeout(seconds)

    def send_line(self, text):
        data = text.encode(ENCODING) + b"\n"
        with self._send_lock:
            try:
                self._sock.sendall(data)
            except OSError as exc:
                raise TransportError(f"send failed: {exc}") from exc

    def recv_line(self):
        """Return the next line, or None when the peer closed the connection."""
        while b"\n" not in self._buffer:
            try:
                chunk = self._sock.recv(4096)
            except OSError as exc:
                raise TransportError(f"receive failed: {exc}") from exc
            if not chunk:
                return None
            self._buffer += chunk
            if len(self._buffer) > MAX_LINE_BYTES:
                raise TransportError("incoming line is too long")
        line, self._buffer = self._buffer.split(b"\n", 1)
        return line.decode(ENCODING, errors="replace").rstrip("\r")

    def close(self):
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        try:
            self._sock.close()
        except OSError:
            pass


def create_server_socket(host, port, backlog=10):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        sock.bind((host, port))
        sock.listen(backlog)
    except OSError as exc:
        sock.close()
        raise TransportError(f"cannot listen on {host}:{port}: {exc}") from exc
    sock.settimeout(1.0)
    return sock


def accept(server_sock):
    """Return (Connection, address), or None after a one second timeout."""
    try:
        conn, addr = server_sock.accept()
    except socket.timeout:
        return None
    except OSError as exc:
        raise TransportError(f"accept failed: {exc}") from exc
    conn.settimeout(None)
    return Connection(conn), addr


def connect(host, port, timeout=5):
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
    except OSError as exc:
        raise TransportError(f"cannot connect to {host}:{port}: {exc}") from exc
    sock.settimeout(None)
    return Connection(sock)
