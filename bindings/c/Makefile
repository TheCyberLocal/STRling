BUILD_DIR ?= build
CMAKE ?= cmake

.PHONY: all configure tests install clean

all: configure
	$(CMAKE) --build $(BUILD_DIR) --config Release

configure:
	$(CMAKE) -S . -B $(BUILD_DIR) -DSTRLING_C_WARNINGS_AS_ERRORS=ON

tests: all
	ctest --test-dir $(BUILD_DIR) -C Release --output-on-failure

install: all
	$(CMAKE) --install $(BUILD_DIR) --config Release

clean:
	$(CMAKE) -E remove_directory $(BUILD_DIR)
