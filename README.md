# VEYE Camera I2C Studio

[English](README.en.md) | **中文**

基于 Web 的 VEYE 相机管理与调试工具。通过浏览器即可对相机进行寄存器级别的读写操作。

> **v0.2.0 版本** — 支持 Jetson、Raspberry Pi 5 和 Rockchip 平台，支持 GX/GXC 系列和 MV/RAW 系列相机。

## 1. 功能

- 自动探测已连接的 VEYE 相机（支持 GX/GXC 系列和 MV/RAW 系列）
- GX 系列：108 条寄存器命令，覆盖相机全部可配置参数
- MV/RAW 系列：76 条寄存器命令，支持传感器寄存器读取
- 寄存器读取 / 写入，支持多种参数类型（数值、枚举、位域）
- 命令分组浏览与搜索
- 中英文双语界面
- 深色 / 浅色主题切换
- 根据相机系列自动过滤可用功能（如触发模式）

## 2. 项目结构

```
veye_camera_i2c_studio/
├── gx_i2c_tools/                   # GX/GXC 系列相机 I2C 工具集
│   ├── gx_mipi_i2c.sh             # 命令行 I2C 读写脚本
│   ├── i2c_functions.sh           # I2C 函数库
│   ├── i2c_vread / i2c_vwrite     # 预编译二进制工具
│   └── source/                    # C 语言源码
├── mv_i2c_tools/                   # MV/RAW 系列相机 I2C 工具集
│   ├── mv_mipi_i2c.sh             # 命令行 I2C 读写脚本
│   ├── lut_rw                     # LUT 读写工具
│   ├── i2c_4read / i2c_4write     # 预编译二进制工具
│   └── sources/                   # C 语言源码
├── veye_camera_web_studio/         # Web 服务主程序
│   ├── main.py                    # FastAPI 入口 (v0.2.0)
│   ├── app/
│   │   ├── adapters/              # 平台适配器
│   │   │   └── jetson/            # Jetson 平台适配
│   │   ├── api/                   # API 路由
│   │   │   ├── devices.py         # 相机探测与系列识别接口
│   │   │   └── commands.py        # 寄存器命令执行接口
│   │   ├── services/              # 业务逻辑层
│   │   │   ├── command_service.py     # 寄存器读写执行
│   │   │   ├── probe_service.py       # 相机探测与系列识别
│   │   │   ├── documentation_service.py # 文档服务
│   │   │   ├── system_service.py      # 系统信息
│   │   │   └── log_service.py         # 操作日志
│   │   ├── static/                # 前端静态文件
│   │   │   ├── app.js
│   │   │   ├── style.css
│   │   │   └── logo*.png
│   │   └── templates/             # HTML 模板
│   │       └── index.html
│   ├── config/                    # 配置文件
│   │   ├── gx_commands.json       # GX 系列 108 条命令定义
│   │   ├── gx_command_groups.json # GX 命令分组
│   │   ├── gx_register.json       # GX 寄存器参考数据
│   │   ├── mv_commands.json       # MV 系列 76 条命令定义
│   │   ├── mv_command_groups.json # MV 命令分组
│   │   ├── mv_register.json       # MV 寄存器参考数据
│   │   ├── default_i2c.json       # 默认 I2C 配置
│   │   └── i18n.json              # 国际化
│   ├── tools/                     # I2C 工具与探测脚本
│   │   ├── i2c_vread / i2c_vwrite     # GX 系列工具（编译产物）
│   │   ├── i2c_4read / i2c_4write     # MV 系列工具（编译产物）
│   │   ├── source/                # C 源码（gx/ 和 mv/ 子目录）
│   │   └── probe/                 # 平台探测脚本
│   ├── scripts/                   # 辅助脚本
│   │   ├── generate_commands.py   # 命令配置生成器
│   │   ├── patch_execution_steps.py # 执行步骤补丁
│   │   └── update_script_functions.py
│   ├── requirements.txt           # Python 依赖
│   └── RELEASE.md                 # 发布说明
├── for_reference/                  # 参考资料（寄存器手册）
├── setup.sh                        # 安装与启动脚本
├── CHANGELOG.md                    # 版本历史
└── README.md / README.en.md        # 项目文档
```

## 3. I2C 工具集

### 3.1 gx_i2c_tools - GX/GXC 系列工具

`gx_i2c_tools/` 目录包含适用于嵌入式平台的通用 GX/GXC 系列相机 I2C 读写工具：

- **gx_mipi_i2c.sh** — 命令行脚本，支持直接读写寄存器
- **i2c_functions.sh** — I2C 操作函数库
- **source/** — C 语言源码，可编译为二进制工具

详细文档请参考：[Gx_mipi_i2c.sh 用户指南](https://wiki.veye.cc/index.php/Gx_mipi_i2c.sh_user_guide)

### 3.2 mv_i2c_tools - MV/RAW 系列工具

`mv_i2c_tools/` 目录包含 MV/RAW 系列相机的 I2C 读写工具：

- **mv_mipi_i2c.sh** — 命令行脚本，支持寄存器读写和 LUT 配置
- **lut_rw** — LUT（查找表）读写工具
- **sources/** — C 语言源码

#### 使用示例

```bash
# GX 系列：读取相机制造商信息
./gx_i2c_tools/gx_mipi_i2c.sh -r manufacturer

# GX 系列：写入恢复出厂参数
./gx_i2c_tools/gx_mipi_i2c.sh -w factoryparam

# MV 系列：读取相机版本
./mv_i2c_tools/mv_mipi_i2c.sh -r version

# MV 系列：读取传感器寄存器
./mv_i2c_tools/mv_mipi_i2c.sh -r snsreg
```

## 4. 技术架构

```
浏览器 (HTML + JS + CSS)
    ↕  HTTP / JSON
FastAPI (Python)
    ↕  系统调用
i2c_vread / i2c_vwrite (GX 系列 C 工具)
i2c_4read / i2c_4write (MV 系列 C 工具)
    ↕  I2C 总线
相机硬件 (GX/GXC 或 MV/RAW 系列)
```

- **后端**: Python 3 + FastAPI + Uvicorn
- **前端**: 原生 JavaScript，无框架依赖
- **硬件通信**: 通过编译好的二进制工具直接操作 I2C 总线
- **系列识别**: 通过 sysfs 自动检测相机系列（GX 或 MV/RAW）

## 5. 快速开始

### 5.1 前置要求

- Python 3.8+
- GCC（用于编译 I2C 工具，仅在无预编译包时需要）
- 支持的平台：
  - **Nvidia Jetson** (JetPack 4.x/5.x)
  - **Raspberry Pi 5** (Debian 12+/Bookworm, aarch64)
  - Raspberry Pi 4 (实验性支持)
  - Rockchip RK3588 (实验性支持)

**树莓派5 额外依赖：**
```bash
sudo apt install media-ctl gawk
```

### 5.2 安装与启动

```bash
# 运行安装脚本（编译 I2C 工具、安装 Python 依赖）
./setup.sh

# 启动服务器
cd veye_camera_web_studio
python3 main.py
```

浏览器打开 `http://localhost:8080` 即可使用。

**注意：** 在树莓派5上，如果网络较慢，可以使用代理：
```bash
# 使用代理安装依赖（可选）
cd veye_camera_web_studio
.venv/bin/pip install --proxy=http://<代理IP>:<端口> -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
```

### 5.3 一键启动

```bash
./setup.sh --start
```

## 6. 已知限制

- **Jetson** 和 **Raspberry Pi 5** 已完全测试
- Rockchip 平台和其他树莓派版本未经充分验证
- 需要 I2C 总线访问权限（可能需要 root 或正确的 udev 规则）
- 多客户端并发访问 I2C 总线时可能出现冲突

## 7. 平台兼容性

| 平台 | 状态 | 备注 |
|------|------|------|
| Nvidia Jetson | ✅ 完全支持 | 原始开发平台 |
| Raspberry Pi 5 | ✅ 完全支持 | Debian 13 / aarch64 已测试 |
| Raspberry Pi 4 | ⚠️ 实验性 | 脚本已包含，待验证 |
| Rockchip RK3588 | ✅ 完全支持 | Orange Pi CM5 已测试 |

## 8. 版本历史

查看 [CHANGELOG.md](CHANGELOG.md) 了解详细的版本更新记录。

## 9. License

MIT
