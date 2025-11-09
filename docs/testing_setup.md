# Test Environment Setup Guide

[← Back to Developer Hub](index.md)

This guide provides **copy-pasteable commands** for setting up your local test environment for both STRling bindings. It assumes you have Python 3.x and Node.js already installed on your system.

---

## Python Binding (`STRling.py`)

### 1. Create Virtual Environment

```bash
python3 -m venv ./bindings/python/.venv
```

### 2. Activate Virtual Environment

**On Linux/macOS:**
```bash
source ./bindings/python/.venv/bin/activate
```

**On Windows:**
```bash
./bindings/python/.venv/Scripts/activate
```

### 3. Install Dependencies

```bash
pip install -r ./bindings/python/requirements.txt
```

### 4. Install STRling in Editable Mode

```bash
pip install -e ./bindings/python
```

### 5. Run Tests

```bash
pytest
```

Or, to run tests from the Python binding directory:

```bash
cd bindings/python
pytest
```

---

## JavaScript Binding (`STRling.js`)

### 1. Set Node Version (if using nvm)

```bash
nvm use 20
```

If you don't have Node.js 20 installed:

```bash
nvm install 20
nvm use 20
```

### 2. Install Dependencies

```bash
cd bindings/javascript
npm install
```

### 3. Run Tests

```bash
npm test
```

---

## Quick Reference

### Python Test Commands

| Command | Description |
|---------|-------------|
| `pytest` | Run all tests |
| `pytest -v` | Run tests with verbose output |
| `pytest tests/unit/` | Run only unit tests |
| `pytest tests/e2e/` | Run only E2E tests |
| `pytest -k "test_name"` | Run specific test by name |

### JavaScript Test Commands

| Command | Description |
|---------|-------------|
| `npm test` | Run all tests |
| `npm test -- --verbose` | Run tests with verbose output |
| `npm test -- __tests__/unit/` | Run only unit tests |
| `npm test -- __tests__/e2e/` | Run only E2E tests |
| `npm test -- -t "test_name"` | Run specific test by name |

---

## Troubleshooting

### Python Issues

**Problem:** `ModuleNotFoundError: No module named 'strling'`

**Solution:** Ensure you've installed the package in editable mode:
```bash
pip install -e ./bindings/python
```

**Problem:** Tests fail with import errors

**Solution:** Make sure your virtual environment is activated and all dependencies are installed:
```bash
source ./bindings/python/.venv/bin/activate
pip install -r ./bindings/python/requirements.txt
```

### JavaScript Issues

**Problem:** `Cannot find module` errors

**Solution:** Ensure dependencies are installed:
```bash
cd bindings/javascript
npm install
```

**Problem:** Wrong Node.js version

**Solution:** Use Node.js 20 or later:
```bash
nvm use 20
```

---

## Related Documentation

- **[Developer Hub](index.md)**: Return to the central documentation hub for all testing guides and standards
