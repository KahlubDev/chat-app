"""Demo. Starts the server and three clients, then saves the terminal output.

Run: python3 run_demo.py   (Windows: py run_demo.py)
Output file: sample_output.txt
"""
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from chat import transport  # noqa: E402
from chat.application import decode, encode, make_message  # noqa: E402

PORT = 5000
lines = []
lock = threading.Lock()


def record(label, text):
    with lock:
        lines.append(f"[{label}] {text}" if label else text)
        print(lines[-1], flush=True)


def section(title):
    record("", "")
    record("", f"=== {title} ===")


def pump(proc, label):
    for raw in proc.stdout:
        record(label, raw.rstrip())


def spawn(label, args):
    proc = subprocess.Popen([sys.executable, "-u"] + args, cwd=ROOT, text=True,
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, bufsize=1)
    threading.Thread(target=pump, args=(proc, label), daemon=True).start()
    return proc


def type_line(proc, label, text):
    record("", f"({label} types) {text}")
    proc.stdin.write(text + "\n")
    proc.stdin.flush()
    time.sleep(0.5)


def main():
    section("1. Server offline: the client prints a clear error")
    offline = spawn("client-test", ["client.py", "--name", "test", "--port", "5999"])
    offline.wait(timeout=10)
    time.sleep(0.3)

    section("2. Start the server and three clients")
    server = spawn("server", ["server.py", "--port", str(PORT)])
    time.sleep(1)
    alice = spawn("alice", ["client.py", "--name", "alice", "--port", str(PORT)])
    time.sleep(0.6)
    bob = spawn("bob", ["client.py", "--name", "bob", "--port", str(PORT)])
    time.sleep(0.6)
    carol = spawn("carol", ["client.py", "--name", "carol", "--port", str(PORT)])
    time.sleep(0.8)

    section("3. Commands, messages, replies and broadcasts")
    type_line(alice, "alice", "/list")
    type_line(alice, "alice", "hello everyone")
    type_line(bob, "bob", "hi alice, hi carol")

    section("4. Malformed message: the server replies with an error")
    raw = transport.connect("127.0.0.1", PORT)
    raw.set_timeout(3)
    raw.send_line(encode(make_message("join", "dave")))
    record("raw-dave", "received: " + raw.recv_line())
    record("raw-dave", "sends: {this is not json")
    raw.send_line("{this is not json")
    record("raw-dave", "received: " + raw.recv_line())
    raw.send_line(encode(make_message("command", "dave", "/quit")))
    record("raw-dave", "received: " + raw.recv_line())
    raw.close()
    time.sleep(0.5)

    section("5. Client disconnects without warning")
    record("", "(carol process is killed)")
    carol.kill()
    time.sleep(1)

    section("6. Clean disconnect with /quit")
    type_line(bob, "bob", "/quit")
    time.sleep(0.5)
    alice.stdin.close()
    alice.wait(timeout=10)
    time.sleep(0.5)
    server.terminate()
    server.wait(timeout=5)
    time.sleep(0.3)

    with open(os.path.join(ROOT, "sample_output.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).lstrip("\n") + "\n")
    print("\nSaved sample_output.txt")


if __name__ == "__main__":
    main()
