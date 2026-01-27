# Makefile for judge queue daemon

CC = gcc
CFLAGS = -std=c99 -Wall -Wextra -Werror -O2 -D_POSIX_C_SOURCE=200809L
LIBS = -lsqlite3 -lcurl

TARGET = judge_queue_daemon

all: $(TARGET)

$(TARGET): judge_queue_daemon.c
	$(CC) $(CFLAGS) -o $(TARGET) judge_queue_daemon.c $(LIBS)

clean:
	rm -f $(TARGET)

install: $(TARGET)
	@echo "Binary ready at ./$(TARGET)"
	@echo "Run with: ./$(TARGET) [--foreground]"
	@echo "Stop with: kill -TERM \$$(cat /tmp/judge-queue.pid)"
	@echo "Logs at: /tmp/judge-queue.log"

.PHONY: all clean install
