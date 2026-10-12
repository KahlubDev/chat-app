"""Automated test. Starts the server, connects clients and prints PASS or FAIL."""
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from chat import transport  # noqa: E402
from chat.application import decode, encode, make_message  # noqa: E402

PORT = 5057
results = []


def check(name, condition):
    results.append(condition)
    print(f"{'PASS' if condition else 'FAIL'}: {name}")


def start_server():
    proc = subprocess.Popen([sys.executable, os.path.join(ROOT, "server.py"),
                             "--port", str(PORT)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(50):
        try:
            transport.connect("127.0.0.1", PORT, timeout=0.5).close()
            return proc
        except transport.TransportError:
            time.sleep(0.1)
    proc.terminate()
    raise RuntimeError("server did not start")


def open_client(name):
    conn = transport.connect("127.0.0.1", PORT)
    conn.set_timeout(3)
    conn.send_line(encode(make_message("join", name)))
    return conn


def read(conn):
    line = conn.recv_line()
    return decode(line) if line is not None else None


def send(conn, msg_type, sender, body):
    conn.send_line(encode(make_message(msg_type, sender, body)))


def run_checks():
    alice = open_client("alice")
    welcome = read(alice)
    check("client receives a welcome message after join",
          welcome is not None and welcome["type"] == "info" and "Welcome alice" in welcome["body"])

    bob = open_client("bob")
    read(bob)
    read(alice)  # alice sees "bob joined"

    send(alice, "chat", "alice", "hello bob")
    ack = read(alice)
    check("sender receives an ack for a chat message",
          ack is not None and ack["type"] == "ack")
    broadcast = read(bob)
    check("other client receives the broadcast",
          broadcast is not None and broadcast["type"] == "broadcast"
          and broadcast["sender"] == "alice" and broadcast["body"] == "hello bob")

    send(alice, "command", "alice", "/list")
    listing = read(alice)
    check("/list returns both users",
          listing is not None and "alice" in listing["body"] and "bob" in listing["body"])

    alice.send_line("this is not json")
    bad = read(alice)
    check("malformed message returns an error and keeps the connection",
          bad is not None and bad["type"] == "error")

    send(alice, "command", "alice", "/nope")
    unknown = read(alice)
    check("unknown command returns an error",
          unknown is not None and unknown["type"] == "error")

    twin = open_client("alice")
    refused = read(twin)
    check("duplicate name is refused",
          refused is not None and refused["type"] == "error")
    twin.close()

    send(bob, "command", "bob", "/quit")
    goodbye = read(bob)
    check("/quit returns goodbye", goodbye is not None and "Goodbye" in goodbye["body"])
    check("server closes the connection after /quit", read(bob) is None)
    bob.close()
    alice.close()


def main():
    proc = start_server()
    try:
        run_checks()
    except (transport.TransportError, RuntimeError, AssertionError) as exc:
        check(f"test run finished without error ({exc})", False)
    finally:
        proc.terminate()
        proc.wait(timeout=5)
    ok = bool(results) and all(results)
    print("RESULT: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
