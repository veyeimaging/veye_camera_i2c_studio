# Compiler
CC = gcc

# Compiler flags
CFLAGS = -Wall

# Common source file
COMMON_SRCS = strfunc.c

# Target executable files
TARGETS = ../i2c_4read ../i2c_4write ../lut_rw

# Default target
all: $(TARGETS)

# Build rule for i2c_4read
../i2c_4read: i2c_4read.c $(COMMON_SRCS)
	$(CC) $(CFLAGS) -o $@ $^

# Build rule for i2c_4write
../i2c_4write: i2c_4write.c $(COMMON_SRCS)
	$(CC) $(CFLAGS) -o $@ $^

# Build rule for lut_rw
../lut_rw: lut_rw.c $(COMMON_SRCS)
	$(CC) $(CFLAGS) -o $@ $^

# Clean target
clean:
	rm -f $(TARGETS)

# Phony targets
.PHONY: all clean
