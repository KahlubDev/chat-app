"""Presentation layer: reads user input and prints output."""
import sys
import threading
from datetime import datetime

_print_lock = threading.Lock()


def _out(text):
    with _print_lock:
        print(text, flush=True)


def read_input(prompt="> "):
    """Read one line from the user. Raise EOFError when input ends."""
    if sys.stdin.isatty():
        return input(prompt)
    line = sys.stdin.readline()
    if line == "":
        raise EOFError
    return line.rstrip("\n")


def format_message(msg):
    stamp = msg["timestamp"][11:19]
    kind = msg["type"]
    if kind == "broadcast":
        return f"[{stamp}] {msg['sender']}: {msg['body']}"
    if kind == "info":
        return f"[{stamp}] * {msg['body']}"
    if kind == "ack":
        return f"[{stamp}] ok: {msg['body']}"
    if kind == "error":
        return f"[{stamp}] ! {msg['body']}"
    return f"[{stamp}] {msg['sender']}: {msg['body']}"


def show_message(msg):
    _out(format_message(msg))


def show_info(text):
    _out(f"* {text}")


def show_error(text):
    _out(f"! Error: {text}")


def log(text):
    """Server log line with a local time stamp."""
    _out(f"{datetime.now().strftime('%H:%M:%S')} {text}")
