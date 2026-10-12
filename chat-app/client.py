"""Chat client. Connects to the server, sends typed lines and prints replies."""
import argparse
import sys
import threading

from chat import presentation as view
from chat import transport
from chat.application import (ProtocolError, decode, encode, make_message,
                              parse_user_input, valid_name)


def receive_loop(conn, state):
    while True:
        try:
            line = conn.recv_line()
        except transport.TransportError as exc:
            if not state["quitting"]:
                view.show_error(f"connection lost: {exc}")
            break
        if line is None:
            if state["quitting"]:
                view.show_info("Disconnected.")
            else:
                view.show_error("the server closed the connection. Press Enter to exit.")
            break
        try:
            msg = decode(line)
        except ProtocolError as exc:
            view.show_error(f"bad message from server: {exc}")
            continue
        view.show_message(msg)
    state["done"].set()


def main():
    parser = argparse.ArgumentParser(description="TCP chat client")
    parser.add_argument("--name", required=True, help="your user name")
    parser.add_argument("--host", default=transport.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=transport.DEFAULT_PORT)
    args = parser.parse_args()

    if not valid_name(args.name):
        view.show_error("invalid name. Use 1 to 20 letters, digits or underscores.")
        return 1
    try:
        conn = transport.connect(args.host, args.port)
    except transport.TransportError:
        view.show_error(f"cannot reach the server at {args.host}:{args.port}. "
                        "Start server.py first.")
        return 1

    state = {"quitting": False, "done": threading.Event()}
    try:
        conn.send_line(encode(make_message("join", args.name)))
        view.show_info(f"Connected to {args.host}:{args.port} as {args.name}. Type /help.")
        receiver = threading.Thread(target=receive_loop, args=(conn, state), daemon=True)
        receiver.start()

        while not state["done"].is_set():
            try:
                text = view.read_input()
            except (EOFError, KeyboardInterrupt):
                text = "/quit"
            msg = parse_user_input(args.name, text)
            if msg is None:
                continue
            if msg["type"] == "command" and msg["body"].lower().startswith("/quit"):
                state["quitting"] = True
            conn.send_line(encode(msg))
            if state["quitting"]:
                state["done"].wait(timeout=3)
                break
    except transport.TransportError as exc:
        view.show_error(f"connection lost: {exc}")
        return 1
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
