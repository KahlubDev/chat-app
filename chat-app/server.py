"""Chat server. Listens on localhost and starts one thread for each client."""
import argparse
import sys
import threading

from chat import presentation as view
from chat import transport
from chat.application import (ChatService, ProtocolError, decode, encode,
                              make_message, SERVER_NAME)


def handle_client(conn, addr, service):
    name = None
    peer = f"{addr[0]}:{addr[1]}"

    def send(msg):
        conn.send_line(encode(msg))

    def send_error(text):
        try:
            send(make_message("error", SERVER_NAME, text))
        except transport.TransportError:
            pass

    try:
        line = conn.recv_line()
        if line is None:
            return
        try:
            first = decode(line)
        except ProtocolError as exc:
            view.log(f"malformed first message from {peer}: {exc}")
            send_error(f"malformed message: {exc}")
            return
        if first["type"] != "join":
            send_error("the first message must be of type join")
            return
        error = service.join(first["sender"], send)
        if error:
            view.log(f"join refused for {peer}: {error}")
            send_error(error)
            return
        name = first["sender"]
        view.log(f"{name} connected from {peer}")

        while True:
            line = conn.recv_line()
            if line is None:
                view.log(f"{name} disconnected without warning")
                break
            try:
                msg = decode(line)
            except ProtocolError as exc:
                view.log(f"malformed message from {name}: {exc}")
                service.reply_error(name, f"malformed message: {exc}")
                continue
            view.log(f"{name} sent {msg['type']}: {msg['body']}")
            if not service.handle(name, msg):
                view.log(f"{name} left with /quit")
                break
    except transport.TransportError as exc:
        view.log(f"connection error with {name or peer}: {exc}")
    finally:
        if name:
            service.leave(name)
        conn.close()


def main():
    parser = argparse.ArgumentParser(description="TCP chat server")
    parser.add_argument("--host", default=transport.DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=transport.DEFAULT_PORT)
    args = parser.parse_args()

    try:
        server_sock = transport.create_server_socket(args.host, args.port)
    except transport.TransportError as exc:
        view.show_error(str(exc))
        return 1

    service = ChatService()
    view.log(f"server listening on {args.host}:{args.port}")
    try:
        while True:
            accepted = transport.accept(server_sock)
            if accepted is None:
                continue
            conn, addr = accepted
            threading.Thread(target=handle_client, args=(conn, addr, service),
                             daemon=True).start()
    except KeyboardInterrupt:
        view.log("server stopped")
    finally:
        server_sock.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
