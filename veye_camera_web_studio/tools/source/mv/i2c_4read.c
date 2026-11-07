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
#include "i2c_4comm.h"

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

static int i2c_rd(int fd, uint8_t i2c_addr, uint16_t reg, uint32_t *values, uint32_t n)
{
	int err;
	int i = 0;
	uint8_t buf[2] = { reg >> 8, reg & 0xff };
    uint8_t bufout[8] = {0};
	struct i2c_rdwr_ioctl_data msgset;
	struct i2c_msg msgs[2] = {
		{
			 .addr = i2c_addr,
			 .flags = 0,
			 .len = 2,
			 .buf = buf,
		},
		{
			.addr = i2c_addr,
			.flags = I2C_M_RD ,
			.len = 4,
			.buf = bufout,
		},
	};

	msgset.msgs = msgs;
	msgset.nmsgs = 2;

	err = ioctl(fd, I2C_RDWR, &msgset);
	//printf("Read i2c addr %02X\n", i2c_addr);
	if (err != msgset.nmsgs)
    {
        printf("Read i2c err %d\n", err);
		return -1;
    }
	for(i = 0; i < n;++i)
	{
        *values = ntohl(*(uint32_t*)bufout);
        //*values = ntohl(*values );
		fprintf(stderr,"addr %04x : value %08x \n",reg+i,values[i]);
	}
	
	return 0;
}


int main(int argc, char *argv[])
{
	U32 I2C_port;
	U32 device_addr;
	U32 reg_addr;
	U32 value[128];
	U32 num = 1;
	int lock_fd = -1;

	if (argc < 4)
	{
		printf("usage: %s <bus_num> <device address(8bit)> <register address(16bits)> <len default:1 max100>. sample: %s 0x0 0xA0 0x1000 0x2\n", argv[0], argv[0]);
		return -1;
	}

	if(StrToNumber(argv[1], &I2C_port) != HI_SUCCESS ) {
		printf("Please input i2c port like 0x100 or 256.\r\n");
		return -1;
	}

	if(StrToNumber(argv[2], &device_addr) != HI_SUCCESS ) {
		printf("Please input dev addr like 0x100 or 256.\r\n");
		return -1;
	}

	if(StrToNumber(argv[3], &reg_addr) != HI_SUCCESS ) {
		printf("Please input reg addr like 0x100 0r 256.\r\n");
		return -1;
	}
	if(argc >=5)
	{
		if(StrToNumber(argv[4], &num) != HI_SUCCESS ) {
			printf("Please input reg addr like 0x100 0r 256.\r\n");
			return -1;
		}
	}
	snprintf(i2c_device_name, sizeof(i2c_device_name), "/dev/i2c-%d", I2C_port);
	//printf("Using i2C device %s\n", i2c_device_name);
	
	//printf("====I2C read:<%#x> <%#x> <%#x>====\n", device_addr, reg_addr, num);
	
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
		close(fd);
		release_i2c_lock(lock_fd);
		return -1;
	}
    
    

	i2c_rd(fd, device_addr,reg_addr, value, num);
	
	close(fd);

	// 2. 操作完成后释放锁
	release_i2c_lock(lock_fd);
	
	fprintf(stdout,"%d",value[0]);
	return value[0];
	
}

