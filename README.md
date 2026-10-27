# VEYE Camera I2C Studio

[English](README.en.md) | **中文**

基于 Web 的 VEYE 相机管理与调试工具。通过浏览器即可对相机进行寄存器级别的读写操作。

> **Beta 版本** — 目前仅在 Jetson 平台经过测试，仅支持 GX/GXC 系列相机。

## 1. 功能

- 自动探测已连接的 VEYE GX/GXC 系列相机
- 108 条寄存器命令，覆盖相机全部可配置参数
- 寄存器读取 / 写入，支持多种参数类型（数值、枚举）
- 命令分组浏览与搜索
- 中英文双语界面
- 深色 / 浅色主题切换

## 2. 项目结构

```
veye_camera_i2c_studio/
├── gx_i2c_tools/                # GX/GXC 系列相机 I2C 工具集
│   ├── gx_mipi_i2c.sh          # 命令行 I2C 读写脚本
│   ├── i2c_functions.sh        # I2C 函数库
│   └── source/                 # C 语言源码
│       ├── i2c_vread.c         # I2C 读取工具源码
│       ├── i2c_vwrite.c        # I2C 写入工具源码
│       ├── i2c_vcomm.h         # I2C 通信头文件
│       ├── strfunc.c           # 字符串处理函数
│       └── Makefile            # 编译配置
├── veye_camera_web_studio/      # Web 服务主程序
│   ├── main.py                 # FastAPI 入口
│   ├── app/
│   │   ├── api/                # API 路由
│   │   │   ├── devices.py      # 相机探测相关接口
│   │   │   └── commands.py     # 寄存器命令相关接口
│   │   ├── services/           # 业务逻辑
│   │   │   ├── command_service.py  # 寄存器读写执行
│   │   │   ├── probe_service.py    # 相机探测
│   │   │   ├── system_service.py   # 系统信息
│   │   │   └── log_service.py      # 操作日志
│   │   ├── static/             # 前端静态文件
│   │   │   ├── app.js
│   │   │   └── style.css
│   │   └── templates/          # HTML 模板
│   │       └── index.html
│   ├── config/
│   │   ├── commands.json       # 108 条寄存器命令定义
│   │   ├── command_groups.json # 命令分组
│   │   ├── i18n.json           # 国际化
│   │   └── gx_register.json    # GX 寄存器参考数据
│   ├── tools/                  # I2C 工具（编译产物）
│   │   ├── i2c_vread
│   │   └── i2c_vwrite
│   └── scripts/                # 辅助脚本
├── for_reference/              # 参考资料
├── setup.sh                    # 安装与启动脚本
└── README.md / README.en.md    # 项目文档
```

## 3. gx_i2c_tools - I2C 工具集

`gx_i2c_tools/` 目录包含适用于嵌入式平台的通用 GX/GXC 系列相机 I2C 读写工具：

- **gx_mipi_i2c.sh** — 命令行脚本，支持直接读写寄存器
- **i2c_functions.sh** — I2C 操作函数库
- **source/** — C 语言源码，可编译为二进制工具

详细文档请参考：[Gx_mipi_i2c.sh 用户指南](https://wiki.veye.cc/index.php/Gx_mipi_i2c.sh_user_guide)

### 3.1 使用示例

```bash
# 读取相机制造商信息
./gx_i2c_tools/gx_mipi_i2c.sh -r manufacturer

# 读取相机型号
./gx_i2c_tools/gx_mipi_i2c.sh -r model

# 写入恢复出厂参数
./gx_i2c_tools/gx_mipi_i2c.sh -w factoryparam
```

## 4. 技术架构

```
浏览器 (HTML + JS + CSS)
    ↕  HTTP / JSON
FastAPI (Python)
    ↕  系统调用
i2c_vread / i2c_vwrite (C 工具)
    ↕  I2C 总线
相机硬件
```

- **后端**: Python 3 + FastAPI + Uvicorn
- **前端**: 原生 JavaScript，无框架依赖
- **硬件通信**: 通过编译好的 `i2c_vread` / `i2c_vwrite` 二进制直接操作 I2C 总线

## 5. 快速开始

### 5.1 前置要求

- Python 3
- GCC（用于编译 I2C 工具）
- Jetson 平台（当前仅支持）

### 5.2 安装与启动

```bash
# 运行安装脚本（编译 I2C 工具、安装 Python 依赖）
./setup.sh

# 启动服务器
cd veye_camera_web_studio
python3 main.py
```

浏览器打开 `http://localhost:8080` 即可使用。

### 5.3 一键启动

```bash
./setup.sh --start
```

## 6. 已知限制

- 仅支持 **GX/GXC 系列**相机（MV 系列尚未适配）
- 仅在 **Jetson** 平台测试过，其他平台（Rockchip、Raspberry Pi）未经充分验证
- 需要 I2C 总线访问权限（可能需要 root 或正确的 udev 规则）
- 多客户端并发访问 I2C 总线时可能出现冲突

## 7. License

MIT
