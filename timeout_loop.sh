#!/bin/bash

# Configuration
TOTAL_TIMEOUT=30  # Default timeout in seconds

usage() {
    echo "Usage: $0 [-t timeout_seconds] command [args...]"
    echo "Example: $0 -t 60 python3 script.py --arg1 value1"
    exit 1
}

# Parse timeout argument if provided
while getopts "t:" opt; do
    case $opt in
        t) TOTAL_TIMEOUT=$OPTARG ;;
        *) usage ;;
    esac
done

# Remove the parsed options from the arguments list
shift $((OPTIND-1))

# Check if a command was provided
if [ $# -eq 0 ]; then
    usage
fi

# Get start time
start_time=$(date +%s)

# Function to check if total timeout is reached
check_timeout() {
    current_time=$(date +%s)
    elapsed=$((current_time - start_time))
    if [ $elapsed -ge $TOTAL_TIMEOUT ]; then
        echo "Total timeout of ${TOTAL_TIMEOUT}s reached. Cleaning up and exiting..."
        # Kill any running process in our process group
        pkill -P $$
        exit 0
    fi
    echo "Time remaining: $((TOTAL_TIMEOUT - elapsed)) seconds"
}

# Function to run command with timeout monitoring
run_with_timeout() {
    # Start the command in background
    "$@" &
    cmd_pid=$!
    
    # Monitor the running command
    while kill -0 $cmd_pid 2>/dev/null; do
        check_timeout
        sleep 1
    done

    # If we get here, the command finished on its own
    wait $cmd_pid
    return $?
}

echo "Starting loop that will run for ${TOTAL_TIMEOUT} seconds..."
echo "Command to run: $@"

# Set up trap for cleanup
trap 'pkill -P $$; exit 1' SIGINT SIGTERM

# Main loop
while true; do
    # Check if we should exit before starting new iteration
    check_timeout
    
    # Run the command with timeout monitoring
    run_with_timeout "$@"
done