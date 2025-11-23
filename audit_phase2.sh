#!/bin/bash

mkdir -p audit_logs_phase2

echo "--- C++ Debug ---"
if [ -f "bindings/cpp/build/conformance_test" ]; then
    echo "Running C++ binary directly..."
    (cd bindings/cpp/build && ./conformance_test) > audit_logs_phase2/cpp_debug.log 2>&1
else
    echo "C++ binary not found." > audit_logs_phase2/cpp_debug.log
fi

echo "--- Go Verbose ---"
if [ -d "bindings/go" ]; then
    echo "Running Go tests verbose..."
    (cd bindings/go && go test -v ./...) > audit_logs_phase2/go_verbose.log 2>&1
fi

echo "--- Python Venv ---"
if [ -d "bindings/python" ]; then
    echo "Running Python tests in venv..."
    (
        cd bindings/python
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        pip install -e .
        pytest tests/
    ) > audit_logs_phase2/python_venv.log 2>&1
fi
