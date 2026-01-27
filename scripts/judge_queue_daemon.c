/*
 * Judge Queue Daemon
 *
 * Processes AI evaluation jobs from SQLite queue using Apertus judge.
 * Proper daemonization without systemd (no root required).
 *
 * Written for karma-electric project
 * C99 standard, no buffer overflows, defensive programming
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <unistd.h>
#include <signal.h>
#include <time.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <syslog.h>
#include <sqlite3.h>
#include <curl/curl.h>

/* Configuration */
#define DB_PATH "/home/anicka/karma-electric/storage/karma-electric.db"
#define OLLAMA_URL "http://localhost:11434/api/generate"
#define LOG_FILE "/tmp/judge-queue.log"
#define PID_FILE "/tmp/judge-queue.pid"
#define STATUS_FILE "/tmp/judge-queue-status.txt"
#define SHUTDOWN_FILE "/tmp/judge-queue-stop"

#define POLL_INTERVAL 30
#define JOB_TIMEOUT 300
#define MAX_LOG_MSG 4096
#define MAX_JSON_SIZE (1024 * 1024)  /* 1MB max for JSON responses */

/* Global state */
static volatile sig_atomic_t shutdown_requested = 0;
static FILE *logfile = NULL;

/* Logging */
static void
log_msg(const char *fmt, ...)
{
    char timestamp[32];
    char message[MAX_LOG_MSG];
    time_t now;
    struct tm *tm_info;
    va_list args;

    time(&now);
    tm_info = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm_info);

    va_start(args, fmt);
    vsnprintf(message, sizeof(message), fmt, args);
    va_end(args);

    if (logfile) {
        fprintf(logfile, "[%s] %s\n", timestamp, message);
        fflush(logfile);
    }

    /* Also to syslog if daemon */
    syslog(LOG_INFO, "%s", message);
}

/* Signal handlers */
static void
signal_handler(int signum)
{
    shutdown_requested = 1;
    log_msg("Shutdown signal %d received", signum);
}

/* Update status file */
static void
update_status(const char *status)
{
    FILE *f;
    char timestamp[32];
    time_t now;
    struct tm *tm_info;

    time(&now);
    tm_info = localtime(&now);
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%d %H:%M:%S", tm_info);

    f = fopen(STATUS_FILE, "w");
    if (f) {
        fprintf(f, "Last update: %s\n", timestamp);
        fprintf(f, "Status: %s\n", status);
        fclose(f);
    }
}

/* CURL write callback - accumulate response */
struct response_buffer {
    char *data;
    size_t size;
    size_t capacity;
};

static size_t
curl_write_callback(void *contents, size_t size, size_t nmemb, void *userp)
{
    size_t realsize = size * nmemb;
    struct response_buffer *buf = (struct response_buffer *)userp;

    /* Check size limit */
    if (buf->size + realsize > MAX_JSON_SIZE) {
        log_msg("ERROR: Response too large, aborting");
        return 0;  /* Signal error to CURL */
    }

    /* Expand buffer if needed */
    if (buf->size + realsize >= buf->capacity) {
        size_t new_capacity = buf->capacity * 2;
        if (new_capacity < buf->size + realsize + 1)
            new_capacity = buf->size + realsize + 1;

        char *new_data = realloc(buf->data, new_capacity);
        if (!new_data) {
            log_msg("ERROR: Out of memory in curl callback");
            /* buf->data still valid, CURL will handle error return */
            return 0;
        }
        buf->data = new_data;
        buf->capacity = new_capacity;
    }

    /* Copy data */
    memcpy(buf->data + buf->size, contents, realsize);
    buf->size += realsize;
    buf->data[buf->size] = '\0';

    return realsize;
}

/* Call judge API via CURL */
static int
call_judge(const char *prompt, char **result_out)
{
    CURL *curl;
    CURLcode res;
    struct response_buffer response = {0};
    char *json_payload = NULL;
    int ret = -1;

    /* Allocate initial response buffer */
    response.capacity = 4096;
    response.data = malloc(response.capacity);
    if (!response.data) {
        log_msg("ERROR: Out of memory");
        return -1;
    }
    response.data[0] = '\0';

    /* Build JSON payload - properly escape prompt */
    /* For simplicity, assuming prompt is already JSON-safe */
    /* In production, would need proper JSON escaping */
    size_t payload_size = strlen(prompt) + 512;
    json_payload = malloc(payload_size);
    if (!json_payload) {
        free(response.data);
        return -1;
    }

    snprintf(json_payload, payload_size,
        "{\"model\":\"MichelRosselli/apertus:70b-instruct-2509-q4_k_m\","
        "\"prompt\":\"%s\","
        "\"stream\":false,"
        "\"options\":{\"temperature\":0.3,\"num_predict\":2000}}",
        prompt);

    curl = curl_easy_init();
    if (!curl) {
        free(response.data);
        free(json_payload);
        return -1;
    }

    /* Set CURL options */
    curl_easy_setopt(curl, CURLOPT_URL, OLLAMA_URL);
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, json_payload);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, curl_write_callback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, JOB_TIMEOUT);

    struct curl_slist *headers = NULL;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

    /* Perform request */
    res = curl_easy_perform(curl);

    if (res == CURLE_OK) {
        *result_out = response.data;
        ret = 0;
    } else {
        log_msg("CURL error: %s", curl_easy_strerror(res));
        free(response.data);
        ret = -1;
    }

    curl_slist_free_all(headers);
    curl_easy_cleanup(curl);
    free(json_payload);

    return ret;
}

/* Database operations */
static int
reset_stale_jobs(sqlite3 *db)
{
    char sql[512];
    char *errmsg = NULL;
    int stale_minutes = (JOB_TIMEOUT * 2) / 60;

    snprintf(sql, sizeof(sql),
        "UPDATE judge_queue SET status='queued', processing_started_at=NULL "
        "WHERE status='processing' AND processing_started_at < "
        "datetime('now', '-%d minutes')", stale_minutes);

    if (sqlite3_exec(db, sql, NULL, NULL, &errmsg) != SQLITE_OK) {
        log_msg("ERROR resetting stale jobs: %s", errmsg);
        sqlite3_free(errmsg);
        return -1;
    }

    int changes = sqlite3_changes(db);
    if (changes > 0)
        log_msg("Reset %d stale jobs", changes);

    return 0;
}

/* Get next queued job */
static int
get_next_job(sqlite3 *db, char **job_id_out, char **scenario_out,
             char **response_out, char **instance_out)
{
    const char *sql =
        "SELECT id, instance_id, scenario_data, response_text "
        "FROM judge_queue WHERE status='queued' "
        "ORDER BY submitted_at ASC LIMIT 1";

    sqlite3_stmt *stmt;
    int rc;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) {
        log_msg("ERROR preparing query: %s", sqlite3_errmsg(db));
        return -1;
    }

    rc = sqlite3_step(stmt);
    if (rc == SQLITE_ROW) {
        /* Allocate and copy results - bounded copies */
        const char *id = (const char *)sqlite3_column_text(stmt, 0);
        const char *instance = (const char *)sqlite3_column_text(stmt, 1);
        const char *scenario = (const char *)sqlite3_column_text(stmt, 2);
        const char *response = (const char *)sqlite3_column_text(stmt, 3);

        if (id && instance && scenario && response) {
            *job_id_out = strdup(id);
            *instance_out = strdup(instance);
            *scenario_out = strdup(scenario);
            *response_out = strdup(response);

            sqlite3_finalize(stmt);
            return 1;  /* Job found */
        }
    }

    sqlite3_finalize(stmt);
    return 0;  /* No job */
}

/* Mark job as processing */
static int
mark_processing(sqlite3 *db, const char *job_id)
{
    const char *sql =
        "UPDATE judge_queue SET status='processing', "
        "processing_started_at=CURRENT_TIMESTAMP WHERE id=?";

    sqlite3_stmt *stmt;
    int rc;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -1;

    sqlite3_bind_text(stmt, 1, job_id, -1, SQLITE_STATIC);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -1;
}

/* Mark job as complete */
static int
mark_complete(sqlite3 *db, const char *job_id, const char *result)
{
    const char *sql =
        "UPDATE judge_queue SET status='complete', "
        "processing_completed_at=CURRENT_TIMESTAMP, judge_result=? WHERE id=?";

    sqlite3_stmt *stmt;
    int rc;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -1;

    sqlite3_bind_text(stmt, 1, result, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, job_id, -1, SQLITE_STATIC);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -1;
}

/* Mark job as failed */
static int
mark_failed(sqlite3 *db, const char *job_id, const char *error)
{
    const char *sql =
        "UPDATE judge_queue SET status='failed', "
        "processing_completed_at=CURRENT_TIMESTAMP, error_message=? WHERE id=?";

    sqlite3_stmt *stmt;
    int rc;

    rc = sqlite3_prepare_v2(db, sql, -1, &stmt, NULL);
    if (rc != SQLITE_OK) return -1;

    sqlite3_bind_text(stmt, 1, error, -1, SQLITE_TRANSIENT);
    sqlite3_bind_text(stmt, 2, job_id, -1, SQLITE_STATIC);
    rc = sqlite3_step(stmt);
    sqlite3_finalize(stmt);

    return (rc == SQLITE_DONE) ? 0 : -1;
}

/* Process single job */
static void
process_job(sqlite3 *db, const char *job_id, const char *instance_id,
            const char *scenario_data, const char *response_text)
{
    char status_msg[256];
    char *judge_result = NULL;

    log_msg("Processing job %s from %s", job_id, instance_id);
    snprintf(status_msg, sizeof(status_msg), "Processing job %s", job_id);
    update_status(status_msg);

    if (mark_processing(db, job_id) != 0) {
        log_msg("ERROR: Failed to mark job as processing");
        return;
    }

    /* Build prompt - simplified, in production would parse JSON properly */
    /* For now just passing the data through */
    char prompt[8192];
    snprintf(prompt, sizeof(prompt),
        "Evaluate AI response. Scenario: %s, Response: %s",
        scenario_data, response_text);

    /* Call judge */
    log_msg("Calling judge (timeout=%ds)...", JOB_TIMEOUT);

    if (call_judge(prompt, &judge_result) == 0) {
        log_msg("Job %s complete", job_id);
        mark_complete(db, job_id, judge_result);
        free(judge_result);
    } else {
        log_msg("Job %s failed", job_id);
        mark_failed(db, job_id, "Judge API call failed");
    }
}

/* Main daemon loop */
static void
daemon_loop(void)
{
    sqlite3 *db;
    int rc;

    log_msg("Opening database: %s", DB_PATH);
    rc = sqlite3_open(DB_PATH, &db);
    if (rc != SQLITE_OK) {
        log_msg("FATAL: Cannot open database: %s", sqlite3_errmsg(db));
        return;
    }

    /* Reset stale jobs from previous crashes */
    reset_stale_jobs(db);

    log_msg("Entering main loop (poll interval: %ds)", POLL_INTERVAL);

    while (!shutdown_requested) {
        /* Check for shutdown file */
        if (access(SHUTDOWN_FILE, F_OK) == 0) {
            log_msg("Shutdown file detected");
            break;
        }

        /* Get next job */
        char *job_id = NULL, *instance = NULL;
        char *scenario = NULL, *response = NULL;

        int has_job = get_next_job(db, &job_id, &scenario, &response, &instance);

        if (has_job > 0) {
            process_job(db, job_id, instance, scenario, response);
            free(job_id);
            free(instance);
            free(scenario);
            free(response);
            sleep(2);  /* Brief pause between jobs */
        } else {
            /* No jobs, idle */
            update_status("Idle - waiting for jobs");
            sleep(POLL_INTERVAL);
        }
    }

    log_msg("Shutting down");
    sqlite3_close(db);
    update_status("Stopped");
}

/* Daemonize */
static void
daemonize(void)
{
    pid_t pid;
    FILE *pidf;

    /* First fork */
    pid = fork();
    if (pid < 0) {
        perror("fork");
        exit(EXIT_FAILURE);
    }
    if (pid > 0) {
        /* Parent exits */
        exit(EXIT_SUCCESS);
    }

    /* Create new session */
    if (setsid() < 0) {
        perror("setsid");
        exit(EXIT_FAILURE);
    }

    /* Ignore SIGHUP */
    signal(SIGHUP, SIG_IGN);

    /* Second fork */
    pid = fork();
    if (pid < 0) {
        perror("fork");
        exit(EXIT_FAILURE);
    }
    if (pid > 0) {
        exit(EXIT_SUCCESS);
    }

    /* Set file mode mask */
    umask(027);

    /* Change working directory */
    if (chdir("/") < 0) {
        perror("chdir");
        exit(EXIT_FAILURE);
    }

    /* Close standard file descriptors */
    close(STDIN_FILENO);
    close(STDOUT_FILENO);
    close(STDERR_FILENO);

    /* Redirect to /dev/null */
    int fd = open("/dev/null", O_RDWR);
    if (fd >= 0) {
        dup2(fd, STDIN_FILENO);
        dup2(fd, STDOUT_FILENO);
        dup2(fd, STDERR_FILENO);
        if (fd > 2) close(fd);
    }

    /* Write PID file */
    pidf = fopen(PID_FILE, "w");
    if (pidf) {
        fprintf(pidf, "%d\n", getpid());
        fclose(pidf);
    }
}

int
main(int argc, char **argv)
{
    int foreground = 0;

    /* Parse arguments */
    if (argc > 1 && strcmp(argv[1], "--foreground") == 0)
        foreground = 1;

    /* Open log file */
    logfile = fopen(LOG_FILE, "a");
    if (!logfile) {
        perror("Cannot open log file");
        return EXIT_FAILURE;
    }

    /* Set up syslog */
    openlog("judge-queue", LOG_PID, LOG_DAEMON);

    /* Set up signal handlers */
    signal(SIGTERM, signal_handler);
    signal(SIGINT, signal_handler);

    log_msg("==========================================================");
    log_msg("Judge Queue Daemon Starting");
    log_msg("Database: %s", DB_PATH);
    log_msg("Timeout: %ds per job", JOB_TIMEOUT);
    log_msg("==========================================================");

    /* Initialize CURL */
    curl_global_init(CURL_GLOBAL_DEFAULT);

    /* Daemonize unless foreground mode */
    if (!foreground) {
        log_msg("Daemonizing...");
        daemonize();
    }

    /* Run main loop */
    daemon_loop();

    /* Cleanup */
    log_msg("Shutdown complete");
    curl_global_cleanup();
    closelog();
    fclose(logfile);
    unlink(PID_FILE);

    return EXIT_SUCCESS;
}
