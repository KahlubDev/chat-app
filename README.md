# TCP Chat Application

A client-server chat application for localhost. The server listens on 127.0.0.1 port 5000 and handles several clients at once with threads. The code uses three layers: presentation, application and transport.

## Requirements

- Python 3.8 or newer
- No packages to install
- No Docker

## Project structure

    chat-app/
      server.py              server entry point
      client.py              client entry point
      run_demo.py            starts a server and three clients, writes sample_output.txt
      sample_output.txt      saved terminal output of the demo
      chat/
        presentation.py      presentation layer
        application.py       application layer
        transport.py         transport layer
      tests/
        test_chat.py         automated test
      docs/
        architecture.svg     architecture diagram
        architecture.png     same diagram as an image

## Run commands

Run each command in order. Open a new terminal for each client.

Windows:

    py server.py
    py client.py --name alice
    py client.py --name bob
    py client.py --name carol

macOS and Linux:

    python3 server.py
    python3 client.py --name alice
    python3 client.py --name bob
    python3 client.py --name carol

Type a line to send a chat message. Use /list to see online users, /help for help and /quit to leave. Press Ctrl+C in the server terminal to stop the server.

Run the automated test:

    py tests/test_chat.py          (Windows)
    python3 tests/test_chat.py     (macOS and Linux)

Run the demo and rebuild sample_output.txt:

    py run_demo.py                 (Windows)
    python3 run_demo.py            (macOS and Linux)

Both scripts use ports 5057 and 5000. Stop any server on port 5000 before the demo.

## Architecture

![Architecture diagram](docs/architecture.png)

| Layer | Module | Job | TCP/IP model |
|---|---|---|---|
| Presentation | chat/presentation.py | Reads user input. Prints messages, errors and the server log. | Application |
| Application | chat/application.py | Builds and parses JSON messages. Runs /list, /help and /quit. Keeps the table of online users. | Application |
| Transport | chat/transport.py | Creates sockets. Sends and receives newline-terminated lines over TCP. | Transport (uses TCP) |

The operating system supplies TCP, IP (127.0.0.1) and the loopback interface. These sit under the transport module in the Transport, Internet and Link layers of the TCP/IP model.

Each layer calls only the layer below. The transport module knows nothing about JSON. The application module knows nothing about sockets. The presentation module knows nothing about the protocol.

## Message format

Each message is one JSON object on one line. A newline ends the message.

| Field | Type | Meaning |
|---|---|---|
| type | string | join, chat, command, info, error, ack or broadcast |
| sender | string | User name, or server for server messages |
| body | string | Message text |
| timestamp | string | UTC time in ISO 8601 format |

Example:

    {"type": "chat", "sender": "alice", "body": "hello", "timestamp": "2026-10-12T10:00:00+00:00"}

Types sent by the client: join, chat, command.
Types sent by the server: info, error, ack, broadcast.

User names use 1 to 20 letters, digits or underscores. A message body holds at most 1000 characters.

## How the client and server interact

1. The server creates a TCP socket, binds 127.0.0.1:5000 and waits for connections.
2. The client opens a TCP connection to the server.
3. The server accepts the connection and starts one thread for this client.
4. The client sends a join message with its name.
5. The server checks the name, adds the user to the table, sends a welcome message to the client and tells the other clients.
6. The user types a line. The client wraps the line in a chat message, or in a command message when the line starts with a slash.
7. The server thread decodes the message and applies the rule.
8. A chat message goes to every other client as a broadcast. The sender gets an ack with the delivery count.
9. A command gets an info reply. An unknown command gets an error reply.
10. On /quit the server sends Goodbye, closes the connection and tells the other clients.
11. If a client dies without warning, the server thread sees the closed socket, removes the user and tells the other clients.

## Error handling

| Case | Behavior |
|---|---|
| Server offline | The client prints: cannot reach the server at host:port. Start server.py first. |
| Client disconnects without warning | The server logs the event, removes the user and informs the other clients. |
| Malformed message | The server replies with an error message, logs the problem and keeps the connection open. |
| Duplicate or invalid name | The server replies with an error message and closes the connection. |
| Server stops while a client runs | The client prints an error message and exits after Enter. |

## Test result

Expected output of tests/test_chat.py:

    PASS: client receives a welcome message after join
    PASS: sender receives an ack for a chat message
    PASS: other client receives the broadcast
    PASS: /list returns both users
    PASS: malformed message returns an error and keeps the connection
    PASS: unknown command returns an error
    PASS: duplicate name is refused
    PASS: /quit returns goodbye
    PASS: server closes the connection after /quit
    RESULT: PASS

The saved demo output is in sample_output.txt.
