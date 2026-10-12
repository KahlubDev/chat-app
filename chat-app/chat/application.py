"""Application layer: message format, input parsing, commands and server logic.

Every message is one JSON object with four fields:
type, sender, body and timestamp.
"""
import json
import re
import threading
from datetime import datetime, timezone

CLIENT_TYPES = {"join", "chat", "command"}
SERVER_TYPES = {"info", "error", "ack", "broadcast"}
ALL_TYPES = CLIENT_TYPES | SERVER_TYPES
FIELDS = ("type", "sender", "body", "timestamp")
SERVER_NAME = "server"
MAX_BODY = 1000
NAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{1,20}$")

HELP_TEXT = "Commands: /list shows online users, /help shows this text, /quit leaves the chat."


class ProtocolError(Exception):
    """Raised when a received line is not a valid chat message."""


def valid_name(name):
    return bool(NAME_PATTERN.match(name)) and name != SERVER_NAME


def make_message(msg_type, sender, body=""):
    return {
        "type": msg_type,
        "sender": sender,
        "body": body,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def encode(msg):
    return json.dumps(msg)


def decode(line):
    try:
        msg = json.loads(line)
    except json.JSONDecodeError:
        raise ProtocolError("message is not valid JSON") from None
    if not isinstance(msg, dict):
        raise ProtocolError("message must be a JSON object")
    missing = [f for f in FIELDS if f not in msg]
    if missing:
        raise ProtocolError("missing field(s): " + ", ".join(missing))
    if not all(isinstance(msg[f], str) for f in FIELDS):
        raise ProtocolError("all fields must be strings")
    if msg["type"] not in ALL_TYPES:
        raise ProtocolError(f"unknown message type '{msg['type']}'")
    return msg


def parse_user_input(sender, text):
    """Turn a typed line into a message. Return None for an empty line."""
    text = text.strip()
    if not text:
        return None
    if text.startswith("/"):
        return make_message("command", sender, text)
    return make_message("chat", sender, text)


class ChatService:
    """Server logic. Keeps the table of online users and applies chat rules."""

    def __init__(self):
        self._clients = {}
        self._lock = threading.Lock()

    def names(self):
        with self._lock:
            return sorted(self._clients)

    def join(self, name, send):
        """Register a user. Return None on success or an error text."""
        if not valid_name(name):
            return "invalid name. Use 1 to 20 letters, digits or underscores."
        with self._lock:
            if name in self._clients:
                return f"name '{name}' is already in use."
            self._clients[name] = send
        welcome = f"Welcome {name}. Online: {', '.join(self.names())}"
        self._deliver(send, make_message("info", SERVER_NAME, welcome))
        self._broadcast(name, make_message("info", SERVER_NAME, f"{name} joined"))
        return None

    def leave(self, name):
        with self._lock:
            removed = self._clients.pop(name, None)
        if removed:
            self._broadcast(name, make_message("info", SERVER_NAME, f"{name} left"))

    def handle(self, name, msg):
        """Apply one message from a joined user. Return False to close the connection."""
        kind = msg["type"]
        body = msg["body"].strip()
        if kind == "chat":
            return self._handle_chat(name, body)
        if kind == "command":
            return self._handle_command(name, body)
        self._reply(name, "error", f"message type '{kind}' is not allowed here")
        return True

    def _handle_chat(self, name, body):
        if not body:
            self._reply(name, "error", "empty message")
        elif len(body) > MAX_BODY:
            self._reply(name, "error", f"message is longer than {MAX_BODY} characters")
        else:
            count = self._broadcast(name, make_message("broadcast", name, body))
            self._reply(name, "ack", f"delivered to {count} other user(s)")
        return True

    def _handle_command(self, name, body):
        command = body.split()[0].lower() if body else ""
        if command == "/list":
            self._reply(name, "info", "Online: " + ", ".join(self.names()))
        elif command == "/help":
            self._reply(name, "info", HELP_TEXT)
        elif command == "/quit":
            self._reply(name, "info", "Goodbye")
            return False
        else:
            self._reply(name, "error", f"unknown command '{command}'. Type /help.")
        return True

    def reply_error(self, name, text):
        self._reply(name, "error", text)

    def _reply(self, name, msg_type, body):
        with self._lock:
            send = self._clients.get(name)
        if send:
            self._deliver(send, make_message(msg_type, SERVER_NAME, body))

    def _broadcast(self, exclude, msg):
        with self._lock:
            targets = [s for n, s in self._clients.items() if n != exclude]
        return sum(1 for send in targets if self._deliver(send, msg))

    @staticmethod
    def _deliver(send, msg):
        try:
            send(msg)
            return True
        except Exception:
            return False
