#!/bin/bash

# Create logs directory
mkdir -p audit_logs

echo "Starting Comprehensive Binding Audit..."
echo "Logs will be saved to audit_logs/"

run_audit() {
    BINDING=$1
    DIR=$2
    CMD=$3
    
    echo "---------------------------------------------------"
    echo "Auditing $BINDING..."
    
    if [ -d "$DIR" ]; then
        # Run the command in a subshell to avoid changing the current directory for the main script
        # We use eval to handle complex commands with && and pipes
        (cd "$DIR" && eval "$CMD") > "audit_logs/${BINDING}.log" 2>&1
        EXIT_CODE=$?
        
        if [ $EXIT_CODE -eq 0 ]; then
            echo "[$BINDING] Execution: SUCCESS"
        else
            echo "[$BINDING] Execution: FAILED (Exit Code: $EXIT_CODE)"
        fi
        echo "Log saved to: audit_logs/${BINDING}.log"
    else
        echo "Directory $DIR not found!" > "audit_logs/${BINDING}.log"
        echo "[$BINDING] Status: MISSING DIRECTORY"
    fi
}

# --- Systems ---
run_audit "c" "bindings/c" "make tests"
run_audit "cpp" "bindings/cpp" "cmake -S . -B build && cmake --build build && ctest --test-dir build --output-on-failure"
run_audit "go" "bindings/go" "go test ./..."
run_audit "rust" "bindings/rust" "cargo test"
run_audit "swift" "bindings/swift" "swift test"

# --- Enterprise ---
run_audit "csharp" "bindings/csharp" "echo 'C# tests not yet implemented'"
run_audit "fsharp" "bindings/fsharp" "dotnet test"
run_audit "java" "bindings/java" "mvn test"
run_audit "kotlin" "bindings/kotlin" "./gradlew test"

# --- Web/Scripting ---
run_audit "dart" "bindings/dart" "dart pub get && dart test"
run_audit "lua" "bindings/lua" "busted"
run_audit "perl" "bindings/perl" "prove -l t"
run_audit "php" "bindings/php" "composer install --prefer-dist --no-progress && vendor/bin/phpunit"
run_audit "python" "bindings/python" "pip install -e . && pytest tests/"
run_audit "r" "bindings/r" "Rscript -e \"testthat::test_dir('tests/testthat')\""
run_audit "ruby" "bindings/ruby" "bundle install && bundle exec rake test"
run_audit "typescript" "bindings/typescript" "npm ci && npm test"

echo "---------------------------------------------------"
echo "Audit Complete. Please analyze the logs in audit_logs/."
