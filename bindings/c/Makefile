CC := gcc
CFLAGS := -std=c11 -O2 -Wall -Wextra -Iinclude
SRCDIR := src
COREDIR := $(SRCDIR)/core
SRCS := $(SRCDIR)/strling.c \
        $(COREDIR)/nodes.c \
        $(COREDIR)/ir.c \
        $(COREDIR)/errors.c
OBJS := $(SRCS:.c=.o)
LIB := libstrling.a

.PHONY: all clean test

all: $(LIB)

$(LIB): $(OBJS)
	$(AR) rcs $@ $^

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

test: all
	@echo "No tests implemented yet."

clean:
	rm -f $(OBJS) $(LIB)
