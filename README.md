# Chat Client

## Overview
A multi-client chat application built using TCP sockets and concurrent programming.

## Features
- Real-time messaging
- Multiple clients supported
- Client-server architecture
- Message history

## Tech Stack
- C (client)
- Python (server)
- TCP sockets
- pthreads

## How to Run

### 1. Build the client
```bash
make
```

### 2. Start the server
```bash
make run-server
```

### 3. Run the client
```bash
make run-client
```

## Notes
- Server runs on `127.0.0.1:10008`
- Start the server before running the client
- Use multiple terminals for multiple users