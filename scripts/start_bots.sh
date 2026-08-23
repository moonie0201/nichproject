#!/bin/bash
#
# start_bots.sh — Multi-bot orchestration via tmux
#
# Manages Telegram, Slack, and Discord URL hook bots with tmux sessions.
# Telegram & Slack: auto-managed tmux sessions (nich-tg, nich-slack)
# Discord: external (hermes gateway)
#
# Usage:
#   ./start_bots.sh [start|status|stop|restart]
#
# Environment:
#   .env file in project root (TELEGRAM_URL_HOOK_ENABLED, SLACK_URL_HOOK_ENABLED, etc.)
#

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────────────────────

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly VENV_PYTHON="${PROJECT_ROOT}/venv/bin/python3"
readonly ENV_FILE="${PROJECT_ROOT}/.env"

# Tmux session names
readonly TG_SESSION="nich-tg"
readonly SLACK_SESSION="nich-slack"

# Default command
COMMAND="${1:-status}"

# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

log_info() {
    echo "[INFO] $*" >&2
}

log_error() {
    echo "[ERROR] $*" >&2
}

log_success() {
    echo "[OK] $*" >&2
}

# Load .env file safely (source only specific vars)
load_env() {
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error ".env file not found at $ENV_FILE"
        return 1
    fi

    # Export only bot-related vars to avoid polluting namespace
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE" 2>/dev/null || true
    set +a
}

# Check if tmux session exists
session_exists() {
    local session="$1"
    tmux has-session -t "$session" 2>/dev/null
}

# Get PID from tmux session
get_session_pid() {
    local session="$1"
    if ! session_exists "$session"; then
        echo ""
        return
    fi

    # Get PID of main process in window 0
    tmux list-panes -t "$session:0" -F "#{pane_pid}" 2>/dev/null | head -1
}

# Check if process is running
is_process_running() {
    local pid="$1"
    [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null
}

# ─────────────────────────────────────────────────────────────────────────────
# START FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

start_telegram() {
    if [[ "${TELEGRAM_URL_HOOK_ENABLED:-0}" != "1" ]]; then
        return 0
    fi

    if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
        log_error "Telegram enabled but TELEGRAM_BOT_TOKEN not set"
        return 1
    fi

    log_info "Starting Telegram bot..."

    if session_exists "$TG_SESSION"; then
        log_info "Telegram session already exists, killing old instance..."
        tmux kill-session -t "$TG_SESSION"
        sleep 0.5
    fi

    # Create new tmux session and run bot
    tmux new-session -d -s "$TG_SESSION" -c "$PROJECT_ROOT" \
        "until $VENV_PYTHON -m auto_publisher.telegram_url_hook; do sleep 5; done"

    sleep 1
    local pid
    pid=$(get_session_pid "$TG_SESSION")

    if is_process_running "$pid"; then
        log_success "Telegram bot started (PID: $pid)"
        return 0
    else
        log_error "Telegram bot failed to start"
        return 1
    fi
}

start_slack() {
    if [[ "${SLACK_URL_HOOK_ENABLED:-0}" != "1" ]]; then
        return 0
    fi

    if [[ -z "${SLACK_BOT_TOKEN:-}" ]] || [[ -z "${SLACK_APP_TOKEN:-}" ]]; then
        log_error "Slack enabled but SLACK_BOT_TOKEN or SLACK_APP_TOKEN not set"
        return 1
    fi

    log_info "Starting Slack bot..."

    if session_exists "$SLACK_SESSION"; then
        log_info "Slack session already exists, killing old instance..."
        tmux kill-session -t "$SLACK_SESSION"
        sleep 0.5
    fi

    # Create new tmux session and run bot
    tmux new-session -d -s "$SLACK_SESSION" -c "$PROJECT_ROOT" \
        "until $VENV_PYTHON -m auto_publisher.slack_url_hook; do sleep 5; done"

    sleep 1
    local pid
    pid=$(get_session_pid "$SLACK_SESSION")

    if is_process_running "$pid"; then
        log_success "Slack bot started (PID: $pid)"
        return 0
    else
        log_error "Slack bot failed to start"
        return 1
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# STATUS FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

check_discord_hermes() {
    # Discord runs via external `hermes gateway run`
    # Check if hermes process is running
    if pgrep -f "hermes gateway" >/dev/null 2>&1; then
        echo "RUNNING"
    else
        echo "EXTERNAL"
    fi
}

get_discord_pid() {
    pgrep -f "hermes gateway" 2>/dev/null | head -1 || echo ""
}

print_status_table() {
    local tg_status="DISABLED"
    local tg_session="-"
    local tg_pid="-"

    local slack_status="DISABLED"
    local slack_session="-"
    local slack_pid="-"

    local discord_status="EXTERNAL"
    local discord_session="(hermes)"
    local discord_pid="-"

    # Telegram
    if [[ "${TELEGRAM_URL_HOOK_ENABLED:-0}" == "1" ]]; then
        tg_session="$TG_SESSION"
        tg_pid=$(get_session_pid "$TG_SESSION")
        if [[ -n "$tg_pid" ]] && is_process_running "$tg_pid"; then
            tg_status="RUNNING"
        else
            tg_status="STOPPED"
        fi
    fi

    # Slack
    if [[ "${SLACK_URL_HOOK_ENABLED:-0}" == "1" ]]; then
        slack_session="$SLACK_SESSION"
        slack_pid=$(get_session_pid "$SLACK_SESSION")
        if [[ -n "$slack_pid" ]] && is_process_running "$slack_pid"; then
            slack_status="RUNNING"
        else
            slack_status="STOPPED"
        fi
    fi

    # Discord
    discord_status=$(check_discord_hermes)
    discord_pid=$(get_discord_pid)
    [[ -z "$discord_pid" ]] && discord_pid="-"

    # Print header
    printf "\n"
    printf "%-12s %-12s %-15s %s\n" "Bot" "Status" "Session" "PID"
    printf "%-12s %-12s %-15s %s\n" "---" "------" "-------" "---"

    # Print rows
    printf "%-12s %-12s %-15s %s\n" "Telegram" "$tg_status" "$tg_session" "$tg_pid"
    printf "%-12s %-12s %-15s %s\n" "Slack" "$slack_status" "$slack_session" "$slack_pid"
    printf "%-12s %-12s %-15s %s\n" "Discord" "$discord_status" "$discord_session" "$discord_pid"
    printf "\n"
}

# ─────────────────────────────────────────────────────────────────────────────
# STOP/RESTART FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────

stop_all() {
    log_info "Stopping all bot sessions..."

    if session_exists "$TG_SESSION"; then
        log_info "Killing Telegram session ($TG_SESSION)..."
        tmux kill-session -t "$TG_SESSION"
    fi

    if session_exists "$SLACK_SESSION"; then
        log_info "Killing Slack session ($SLACK_SESSION)..."
        tmux kill-session -t "$SLACK_SESSION"
    fi

    log_success "All bot sessions stopped"
}

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

print_usage() {
    cat <<EOF
Usage: $(basename "$0") [COMMAND]

Commands:
  start       Start all enabled bots in tmux sessions
  status      Show status of all bots (default)
  stop        Stop all bot tmux sessions
  restart     Stop and start all bots
  help        Print this message

Environment Variables (.env):
  TELEGRAM_URL_HOOK_ENABLED    Enable Telegram bot (0/1)
  TELEGRAM_BOT_TOKEN           Telegram bot token
  SLACK_URL_HOOK_ENABLED       Enable Slack bot (0/1)
  SLACK_BOT_TOKEN              Slack bot token
  SLACK_APP_TOKEN              Slack app token

Sessions:
  Telegram: $TG_SESSION
  Slack:    $SLACK_SESSION
  Discord:  external (hermes gateway)

EOF
}

main() {
    case "${COMMAND}" in
        start)
            load_env || exit 1
            log_info "Starting bots..."
            start_telegram || true
            start_slack || true
            sleep 1
            print_status_table
            ;;
        status)
            load_env || true  # Don't exit if .env missing for status
            print_status_table
            ;;
        stop)
            stop_all
            ;;
        restart)
            stop_all
            sleep 1
            load_env || exit 1
            log_info "Starting bots..."
            start_telegram || true
            start_slack || true
            sleep 1
            print_status_table
            ;;
        help|--help|-h)
            print_usage
            exit 0
            ;;
        *)
            log_error "Unknown command: $COMMAND"
            print_usage
            exit 1
            ;;
    esac
}

# Verify tmux is available
if ! command -v tmux &>/dev/null; then
    log_error "tmux is required but not installed"
    exit 1
fi

# Verify Python venv exists
if [[ ! -f "$VENV_PYTHON" ]]; then
    log_error "Python venv not found at $VENV_PYTHON"
    exit 1
fi

# Run main
main "$@"
