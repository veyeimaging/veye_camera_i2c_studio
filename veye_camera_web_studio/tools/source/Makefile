# Compiler
CC = gcc

# Compiler flags
CFLAGS = -Wall

# GX series source files
GX_DIR = gx
GX_COMMON_SRCS = $(GX_DIR)/strfunc.c
GX_TARGETS = ../i2c_vread ../i2c_vwrite

# MV/RAW series source files
MV_DIR = mv
MV_COMMON_SRCS = $(MV_DIR)/strfunc.c
MV_TARGETS = ../i2c_4read ../i2c_4write

# All targets
TARGETS = $(GX_TARGETS) $(MV_TARGETS)

# Default target: build all
all: $(TARGETS)

# ---- GX series ----

../i2c_vread: $(GX_DIR)/i2c_vread.c $(GX_COMMON_SRCS)
	$(CC) $(CFLAGS) -I$(GX_DIR) -o $@ $^

../i2c_vwrite: $(GX_DIR)/i2c_vwrite.c $(GX_COMMON_SRCS)
	$(CC) $(CFLAGS) -I$(GX_DIR) -o $@ $^

# ---- MV/RAW series ----

../i2c_4read: $(MV_DIR)/i2c_4read.c $(MV_COMMON_SRCS)
	$(CC) $(CFLAGS) -I$(MV_DIR) -o $@ $^

../i2c_4write: $(MV_DIR)/i2c_4write.c $(MV_COMMON_SRCS)
	$(CC) $(CFLAGS) -I$(MV_DIR) -o $@ $^

# Clean target
clean:
	rm -f $(TARGETS)

# Phony targets
.PHONY: all clean
