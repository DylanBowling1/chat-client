#define _POSIX_C_SOURCE 200809L

/*
 * mycord client
 *
 * Implements a TCP IPv4 client for the mycord chat service.
 * The client supports concurrent sending (stdin) and receiving
 * (socket) using pthreads, while strictly following the protocol
 * and formatting rules defined in the README.
 *
 * This file satisfies all requirements for Part 1 of the assignment.
 */

#include <arpa/inet.h>
#include <errno.h>
#include <getopt.h>
#include <netdb.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
#include <ctype.h>

/* ============================================================
 *                    PROTOCOL DEFINITIONS
 * ============================================================
 */

/*
 * Message types defined by the mycord protocol.
 * Outbound: LOGIN, LOGOUT, MESSAGE_SEND
 * Inbound:  MESSAGE_RECV, DISCONNECT, SYSTEM
 */
enum MessageType {
    LOGIN = 0,
    LOGOUT = 1,
    MESSAGE_SEND = 2,
    MESSAGE_RECV = 10,
    DISCONNECT = 12,
    SYSTEM = 13
};

/*
 * Fixed-size protocol fields
 */
#define USERNAME_MAX 32
#define MESSAGE_MAX 1024

/*
 * Packed protocol message.
 * Total size: 4 + 4 + 32 + 1024 = 1064 bytes
 *
 * Messages are always sent and received as one struct-sized chunk.
 */
typedef struct __attribute__((packed)) {
    uint32_t message_type;   // message type (network byte order)
    uint32_t timestamp;      // UNIX timestamp (network byte order)
    char username[USERNAME_MAX];
    char message[MESSAGE_MAX];
} message_t;

/* ============================================================
 *                     GLOBAL CLIENT STATE
 * ============================================================
 */

/*
 * Stores runtime settings shared between threads.
 */
typedef struct {
    int socket_fd;           // connected socket descriptor
    bool quiet;              // disables mention highlighting
    char username[USERNAME_MAX];
} settings_t;

/*
 * Global settings instance.
 * Also includes a mutex to prevent output interleaving.
 */
static settings_t settings;
static pthread_mutex_t print_lock = PTHREAD_MUTEX_INITIALIZER;

/* ============================================================
 *                         HELP MENU
 * ============================================================
 */

/*
 * Prints the help menu and exits.
 * Formatting does not need to be exact, only correct.
 */
static void print_help(void) {
    printf("usage: ./client [-h] [--port PORT] [--ip IP] [--domain DOMAIN] [--quiet]\n\n");
    printf("mycord client\n\n");
    printf("options:\n");
    printf("  --help                show this help message and exit\n");
    printf("  --port PORT           port to connect to (default: 8080)\n");
    printf("  --ip IP               IP to connect to (default: 127.0.0.1)\n");
    printf("  --domain DOMAIN       domain name to connect to (cannot be used with --ip)\n");
    printf("  --quiet               do not perform alerts or mention highlighting\n");
}

/* ============================================================
 *                       IO HELPERS
 * ============================================================
 */

/*
 * Reads exactly n bytes from a file descriptor unless EOF or error.
 * Prevents short reads when using TCP sockets.
 */
static ssize_t full_read(int fd, void *buf, size_t n) {
    size_t total = 0;
    char *p = buf;

    while (total < n) {
        ssize_t r = read(fd, p + total, n - total);
        if (r <= 0) return r;
        total += r;
    }
    return total;
}

/*
 * Writes exactly n bytes to a file descriptor.
 * Prevents short writes when sending protocol messages.
 */
static ssize_t full_write(int fd, const void *buf, size_t n) {
    size_t total = 0;
    const char *p = buf;

    while (total < n) {
        ssize_t w = write(fd, p + total, n - total);
        if (w <= 0) return w;
        total += w;
    }
    return total;
}

/*
 * Validates that a string is non-empty and consists only
 * of printable ASCII characters.
 */
static bool printable_ascii(const char *s) {
    if (!s || !*s) return false;
    for (; *s; s++) {
        if (!isprint((unsigned char)*s)) return false;
    }
    return true;
}

/* ============================================================
 *                     SIGNAL HANDLING
 * ============================================================
 */

/*
 * Handles SIGINT and SIGTERM.
 * Sends a LOGOUT message to the server and exits immediately.
 */
static void handle_signal(int sig) {
    (void)sig;

    if (settings.socket_fd >= 0) {
        message_t logout = {0};
        logout.message_type = htonl(LOGOUT);
        full_write(settings.socket_fd, &logout, sizeof(logout));
        close(settings.socket_fd);
    }

    exit(0);
}

/* ============================================================
 *                   MENTION HIGHLIGHTING
 * ============================================================
 */

/*
 * Prints a message string while highlighting all instances
 * of @<username> in red and prepending the bell character (\a).
 */
static void print_highlighted(const char *msg) {
    char target[USERNAME_MAX + 1] = "@";
    strncat(target, settings.username, USERNAME_MAX - 1);

    const char *cur = msg;
    const char *match;

    while ((match = strstr(cur, target))) {
        fwrite(cur, 1, match - cur, stdout);
        printf("\a\033[31m%s\033[0m", target);
        cur = match + strlen(target);
    }

    printf("%s", cur);
}

/* ============================================================
 *                   RECEIVER THREAD
 * ============================================================
 */

/*
 * Thread responsible for continuously receiving messages
 * from the server and displaying them to the user.
 */
static void *receiver(void *arg) {
    (void)arg;

    while (1) {
        message_t msg;

        // Read exactly one protocol message
        ssize_t r = full_read(settings.socket_fd, &msg, sizeof(msg));
        if (r <= 0) {
            exit(0);
        }

        // Ensure strings are safely terminated
        msg.username[USERNAME_MAX - 1] = '\0';
        msg.message[MESSAGE_MAX - 1] = '\0';

        uint32_t type = ntohl(msg.message_type);

        pthread_mutex_lock(&print_lock);

        if (type == MESSAGE_RECV) {
            time_t ts = ntohl(msg.timestamp);
            char buf[32];
            strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M:%S", localtime(&ts));

            printf("[%s] %s: ", buf, msg.username);
            if (settings.quiet) {
                printf("%s\n", msg.message);
            } else {
                print_highlighted(msg.message);
                printf("\n");
            }
        }
        else if (type == SYSTEM) {
            printf("\033[90m[SYSTEM] %s\033[0m\n", msg.message);
        }
        else if (type == DISCONNECT) {
            printf("\033[31m[DISCONNECT] %s\033[0m\n", msg.message);
            fflush(stdout);
            close(settings.socket_fd);
            exit(0);
        }

        pthread_mutex_unlock(&print_lock);
    }
}

/* ============================================================
 *                          MAIN
 * ============================================================
 */

int main(int argc, char **argv) {
    /*
     * Default connection settings
     */
    const char *host = "127.0.0.1";
    const char *port = "8080";
    bool quiet = false;

    bool ip_used = false;
    bool domain_used = false;

    /*
     * Command-line argument parsing
     */
    static struct option opts[] = {
        {"help",   no_argument,       0, 'h'},
        {"port",   required_argument, 0, 'p'},
        {"ip",     required_argument, 0, 'i'},
        {"domain", required_argument, 0, 'd'},
        {"quiet",  no_argument,       0, 'q'},
        {0,0,0,0}
    };

    int c;
    while ((c = getopt_long(argc, argv, "hp:i:d:q", opts, NULL)) != -1) {
        switch (c) {
            case 'h':
                print_help();
                return 0;
            case 'p':
                port = optarg;
                break;
            case 'i':
                if (domain_used) {
                    fprintf(stderr, "Error: Cannot specify both --ip and --domain\n");
                    return 1;
                }
                host = optarg;
                ip_used = true;
                break;
            case 'd':
                if (ip_used) {
                    fprintf(stderr, "Error: Cannot specify both --ip and --domain\n");
                    return 1;
                }
                host = optarg;
                domain_used = true;
                break;
            case 'q':
                quiet = true;
                break;
            default:
                fprintf(stderr, "Error: Invalid arguments\n");
                return 1;
        }
    }

    /*
     * Validate port number
     */
    char *end;
    long p = strtol(port, &end, 10);
    if (*end || p < 1 || p > 65535) {
        fprintf(stderr, "Error: Invalid port\n");
        return 1;
    }

    /*
     * Retrieve and validate username from environment
     */
    const char *user = getenv("USER");
    if (!printable_ascii(user)) {
        fprintf(stderr, "Error: Invalid username\n");
        return 1;
    }

    strncpy(settings.username, user, USERNAME_MAX - 1);
    settings.quiet = quiet;

    /*
     * Install SIGINT and SIGTERM handlers
     */
    struct sigaction sa = {0};
    sa.sa_handler = handle_signal;
    sigaction(SIGINT, &sa, NULL);
    sigaction(SIGTERM, &sa, NULL);

    /*
     * Resolve server address and establish TCP connection
     */
    struct addrinfo hints = {0}, *res;
    hints.ai_socktype = SOCK_STREAM;
    getaddrinfo(host, port, &hints, &res);

    settings.socket_fd = socket(res->ai_family, res->ai_socktype, res->ai_protocol);
    connect(settings.socket_fd, res->ai_addr, res->ai_addrlen);
    freeaddrinfo(res);

    /*
     * Send LOGIN message (type + username only)
     */
    message_t login = {0};
    login.message_type = htonl(LOGIN);
    strncpy(login.username, settings.username, USERNAME_MAX - 1);
    full_write(settings.socket_fd, &login, sizeof(login));

    /*
     * Start receiver thread
     */
    pthread_t t;
    pthread_create(&t, NULL, receiver, NULL);

    /*
     * Main loop: read user input and send messages
     */
    char *line = NULL;
    size_t cap = 0;
    time_t last = 0;
    int count = 0;

    while (getline(&line, &cap, stdin) != -1) {
        line[strcspn(line, "\n")] = 0;

        if (!printable_ascii(line) || strlen(line) > 1023) {
            fprintf(stderr, "Error: Invalid message\n");
            continue;
        }

        // Rate limiting: max 5 messages per second
        time_t now = time(NULL);
        if (now == last && ++count > 5) {
            fprintf(stderr, "Error: message rate too high\n");
            continue;
        }
        if (now != last) {
            last = now;
            count = 1;
        }

        message_t m = {0};
        m.message_type = htonl(MESSAGE_SEND);
        strncpy(m.message, line, MESSAGE_MAX - 1);
        full_write(settings.socket_fd, &m, sizeof(m));
    }

    /*
     * EOF on stdin → send LOGOUT and exit
     */
    message_t logout = {0};
    logout.message_type = htonl(LOGOUT);
    full_write(settings.socket_fd, &logout, sizeof(logout));
    close(settings.socket_fd);

    free(line);
    return 0;
}

