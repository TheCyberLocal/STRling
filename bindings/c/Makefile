CC := gcc
CFLAGS := -std=c11 -O2 -Wall -Wextra -Iinclude -D_POSIX_C_SOURCE=200809L
LDFLAGS := -ljansson
SRCDIR := src
COREDIR := $(SRCDIR)/core
SRCS := $(SRCDIR)/strling.c \
	$(SRCDIR)/compat.c \
	$(COREDIR)/nodes.c \
        $(COREDIR)/ir.c \
        $(COREDIR)/errors.c
OBJS := $(SRCS:.c=.o)
LIB := libstrling.a

# Dependencies
DEPSDIR := deps
PARSON_OBJ := $(DEPSDIR)/parson.o

# Test configuration
TESTDIR := tests
TEST_CFLAGS := $(CFLAGS) -include setjmp.h -include string.h
TEST_LDFLAGS := -lcmocka $(LDFLAGS)
UNIT_TESTS := $(wildcard $(TESTDIR)/unit/*_test.c)
E2E_TESTS := $(wildcard $(TESTDIR)/e2e/*_test.c)
ALL_TESTS := $(UNIT_TESTS) $(E2E_TESTS)
TEST_BINS := $(ALL_TESTS:.c=)

# Conformance test (Dynamic Runner)
CONFORMANCE_SRC := $(TESTDIR)/conformance_test.c
CONFORMANCE_BIN := $(TESTDIR)/conformance_test
TEST_BINS += $(CONFORMANCE_BIN)

.PHONY: all clean tests help

all: $(LIB)

$(LIB): $(OBJS)
	$(AR) rcs $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

$(PARSON_OBJ): $(DEPSDIR)/parson.c
	$(CC) $(CFLAGS) -c $< -o $@

# Build individual test binaries
TEST_HELPERS := $(TESTDIR)/test_helpers.c

# Specific rule for conformance test (overrides pattern rule)
$(CONFORMANCE_BIN): $(CONFORMANCE_SRC) $(LIB) $(PARSON_OBJ)
	$(CC) $(CFLAGS) $< $(PARSON_OBJ) -o $@ $(LIB) $(LDFLAGS)

$(TESTDIR)/%_test: $(TESTDIR)/%_test.c $(LIB) $(TEST_HELPERS)
	$(CC) $(TEST_CFLAGS) $< $(TEST_HELPERS) -o $@ $(LIB) $(TEST_LDFLAGS)

# Build all tests
build-tests: $(TEST_BINS)

# Run all tests
tests: $(LIB) build-tests
	@echo "Running tests..."
	@passed=0; failed=0; \
	for test in $(TEST_BINS); do \
		echo "Running $$test..."; \
		if ./$$test; then \
			passed=$$((passed + 1)); \
		else \
			failed=$$((failed + 1)); \
		fi; \
	done; \
	echo ""; \
	echo "========================================"; \
	echo "Test Summary: $$passed passed, $$failed failed"; \
	echo "========================================"

# Run specific test
test-%: $(TESTDIR)/%_test
	@echo "Running $<..."
	@./$<

clean:
	rm -f $(OBJS) $(LIB) $(TEST_BINS)

help:
	@echo "STRling C Binding Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all          - Build the library (default)"
	@echo "  tests        - Build and run all tests"
	@echo "  build-tests  - Build test binaries without running"
	@echo "  test-<name>  - Run a specific test"
	@echo "  clean        - Remove build artifacts"
	@echo "  help         - Show this help message"
