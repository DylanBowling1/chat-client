CC = gcc
CFLAGS = -Wall -Wextra -pthread

PORT = 10008
HOST = 127.0.0.1

all: client

client: client.c
	$(CC) $(CFLAGS) client.c -o client

clean:
	rm -f client

run-server:
	python3 server.py $(PORT)

run-client:
	./client --ip $(HOST) --port $(PORT)

run: client
	python3 server.py $(PORT) & \
	SERVER_PID=$$!; \
	sleep 1; \
	./client --ip $(HOST) --port $(PORT); \
	kill $$SERVER_PID