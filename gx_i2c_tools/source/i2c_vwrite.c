
#include <ctype.h>
#include <fcntl.h>
#include <libgen.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <linux/i2c.h>
#include <linux/i2c-dev.h>
#include <sys/ioctl.h>
#include <sys/file.h>
#include <unistd.h>
#include <arpa/inet.h>
#include "i2c_vcomm.h"

#define I2C_DEVICE_NAME_LEN 13	// "/dev/i2c-XXX"+NULL
#define I2C_LOCK_PATH_TEMPLATE "/tmp/i2c-%d.lock"
static char i2c_device_name[I2C_DEVICE_NAME_LEN];

// 获取 I2C 总线锁
static int acquire_i2c_lock(uint32_t bus_num, int *lock_fd) {
    char lock_path[32];
    snprintf(lock_path, sizeof(lock_path), I2C_LOCK_PATH_TEMPLATE, bus_num);
    
    *lock_fd = open(lock_path, O_CREAT | O_RDWR, 0666);
    if (*lock_fd < 0) {
        fprintf(stderr, "Failed to open lock file %s: %s\n", lock_path, strerror(errno));
        return -1;
    }
    
    // 获取排他锁（阻塞等待）
    if (flock(*lock_fd, LOCK_EX) < 0) {
        fprintf(stderr, "Failed to acquire lock %s: %s\n", lock_path, strerror(errno));
        close(*lock_fd);
        *lock_fd = -1;
        return -1;
    }
    
    return 0;
}

// 释放 I2C 总线锁
static void release_i2c_lock(int lock_fd) {
    if (lock_fd >= 0) {
        flock(lock_fd, LOCK_UN);
        close(lock_fd);
    }
}

static int gxcam_writel_reg(int fd,	uint8_t i2c_addr, uint16_t reg, uint32_t val)
{
	struct write_regs wr;

	wr.head = WRITE_HEAD;
	wr.reg = htons(reg);
	wr.data = htonl(val);
	wr.xor = xor8((uint8_t *)&wr, sizeof(wr) - 1);
/*	return write(fd, &wr,sizeof(wr));
*/
	struct i2c_rdwr_ioctl_data msgset;
	struct i2c_msg msg = {
		.addr = i2c_addr,
		.flags = 0,
		.len = sizeof(wr),
		.buf = (uint8_t *)&wr,
	};

	msgset.msgs = &msg;
	msgset.nmsgs = 1;

	if (ioctl(fd, I2C_RDWR, &msgset) != msgset.nmsgs)
    {
        printf("Write i2c err \n");
		return -1;
    }
	return 0;
}


int main(int argc, char *argv[])
{
	uint32_t I2C_port;
	uint32_t device_addr;
	uint32_t reg_addr;
	uint32_t new_data;
	int lock_fd = -1;

	if (argc < 5)
	{
		printf("usage: %s <bus_num> <device address 8bits> <register address 32bits> <value>. sample: %s 0x0 0xA0 0x10 0x40\n", argv[0], argv[0]);
		return -1;
	}

	if(StrToNumber(argv[1], &I2C_port) != HI_SUCCESS ) 
	{
		printf("Please input i2c port like 0x100 or 256.\r\n");
		return -1;
	}

	if(StrToNumber(argv[2], &device_addr) != HI_SUCCESS ) 
	{
		printf("Please input dev addr like 0x100 or 256.\r\n");
		return -1;
	}

	if(StrToNumber(argv[3], &reg_addr) != HI_SUCCESS ) 
	{
		printf("Please input reg addr like 0x100 0r 256.\r\n");
		return -1;
	}

	if(StrToNumber(argv[4], &new_data) != HI_SUCCESS ) 
	{
		printf("Please input len like 0x100\n");
		return -1;
	}

	//printf("====I2C write:<%#x> <%#x> <%#x> <%#x>====\n", device_addr, WRITE_HEAD, reg_addr, new_data);
	
	snprintf(i2c_device_name, sizeof(i2c_device_name), "/dev/i2c-%d", I2C_port);
	//printf("Using i2C device %s\n", i2c_device_name);
	
	// 1. 先获取锁
	if (acquire_i2c_lock(I2C_port, &lock_fd) < 0) {
		return -1;
	}

	int fd;
	fd = open(i2c_device_name, O_RDWR);
	if (!fd)
	{
		printf("Couldn't open I2C device\n");
		release_i2c_lock(lock_fd);
		return -1;
	}
	if (ioctl(fd, I2C_SLAVE_FORCE, device_addr) < 0)
	{
		printf("Failed to set I2C address\n");
		fprintf(stderr, "Error: %s\n", strerror(errno));
		close(fd);
		release_i2c_lock(lock_fd);
		return -1;
	}
	if(gxcam_writel_reg(fd,device_addr, reg_addr, new_data) < 0)
	{
		printf("Write i2c err\n");
		close(fd);
		release_i2c_lock(lock_fd);
		return -1;
	}
	close(fd);

	// 2. 操作完成后释放锁
	release_i2c_lock(lock_fd);
	
	return 0;

}

