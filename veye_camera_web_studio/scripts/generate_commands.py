#!/usr/bin/env python3
"""Generate commands.json from register definitions and script analysis."""
import json
import os

WIKI_URL = "https://wiki.veye.cc/index.php/Gx_Series_MIPI_Camera_Register_Map"
PLATFORMS = ["jetson", "rpi", "rpi5", "rk3588"]

def cmd(cid, name_en, name_zh, desc_en, desc_zh, group, mode, risk,
        reg_addr=None, reg_type="arm", params=None, requires_confirm=False,
        update_timing="A", notes_en=None, notes_zh=None, examples=None,
        value_transform=None, cap_modes=None):
    """Build a command dict. cap_modes: list of VideoModeCap values for which this command is relevant.
    1=ROI mode, 2=Preset mode. None means always shown."""
    c = {
        "id": cid,
        "name": {"en": name_en, "zh": name_zh},
        "description": {"en": desc_en, "zh": desc_zh},
        "group": group,
        "mode": mode,
        "risk_level": risk,
        "register": {"address": reg_addr, "reg_type": reg_type} if reg_addr else None,
        "parameters": params or [],
        "requires_confirmation": requires_confirm,
        "update_timing": update_timing,
        "platforms": list(PLATFORMS),
        "wiki_url": WIKI_URL,
        "examples": examples or [],
        "notes": {}
    }
    if notes_en or notes_zh:
        c["notes"] = {"en": notes_en or "", "zh": notes_zh or ""}
    if value_transform:
        c["register"]["value_transform"] = value_transform
    if cap_modes is not None:
        c["cap_modes"] = cap_modes
    return c

def enum_param(name_en, name_zh, desc_en, desc_zh, options, required=True):
    return {
        "name": name_en.lower().replace(" ", "_"),
        "label": {"en": name_en, "zh": name_zh},
        "type": "enum",
        "options": options,
        "required": required,
        "description": {"en": desc_en, "zh": desc_zh}
    }

def int_param(name_en, name_zh, desc_en, desc_zh, mn=None, mx=None, step=1, default=None, required=True, unit=None):
    p = {
        "name": name_en.lower().replace(" ", "_"),
        "label": {"en": name_en, "zh": name_zh},
        "type": "integer",
        "min": mn, "max": mx, "step": step,
        "default": default,
        "required": required,
        "description": {"en": desc_en, "zh": desc_zh}
    }
    if unit:
        p["unit"] = unit
    return p

def float_param(name_en, name_zh, desc_en, desc_zh, mn=None, mx=None, step=0.1, default=None, required=True, unit=None):
    p = {
        "name": name_en.lower().replace(" ", "_"),
        "label": {"en": name_en, "zh": name_zh},
        "type": "float",
        "min": mn, "max": mx, "step": step,
        "default": default,
        "required": required,
        "description": {"en": desc_en, "zh": desc_zh}
    }
    if unit:
        p["unit"] = unit
    return p

def example(desc_en, desc_zh, command):
    return {"description": {"en": desc_en, "zh": desc_zh}, "command": command}

commands = []

# ==================== B1. Device Information (Read-only) ====================
commands.append(cmd("manufacturer", "Manufacturer", "制造商",
    "Read the manufacturer name. Register value (32-bit): 0x56455945 = ASCII \"VEYE\".",
    "读取制造商名称。寄存器值（32位）：0x56455945 = ASCII \"VEYE\"。",
    "device_info", "read", "none", "0x0000"))

commands.append(cmd("model", "Model", "型号",
    "Read the product model code.\n"
    "0x0662: GX-MIPI-IMX662, 0x0234: GX-MIPI-AR0234, 0x0664: GX-MIPI-IMX664,\n"
    "0x8662: GXC-MIPI-IMX662, 0x8234: GXC-MIPI-AR0234, 0x8664: GXC-MIPI-IMX664,\n"
    "0xC002: GXC-MIPI-GMAX4002CG, 0xD002: GXC-MIPI-GMAX4002MG,\n"
    "0x0535: GXC-MIPI-SC535CG, 0x4535: GXC-MIPI-SC535MG,\n"
    "0x0285: GXC-MIPI-SC285CR, 0x0485: GXC-MIPI-SC485CR,\n"
    "0x0136: GXC-MIPI-SC136CG, 0x8136: GXC-MIPI-SC136MG, 0x0235: GXC-MIPI-SC235CR.",
    "读取产品型号代码。\n"
    "0x0662: GX-MIPI-IMX662, 0x0234: GX-MIPI-AR0234, 0x0664: GX-MIPI-IMX664,\n"
    "0x8662: GXC-MIPI-IMX662, 0x8234: GXC-MIPI-AR0234, 0x8664: GXC-MIPI-IMX664,\n"
    "0xC002: GXC-MIPI-GMAX4002CG, 0xD002: GXC-MIPI-GMAX4002MG,\n"
    "0x0535: GXC-MIPI-SC535CG, 0x4535: GXC-MIPI-SC535MG,\n"
    "0x0285: GXC-MIPI-SC285CR, 0x0485: GXC-MIPI-SC485CR,\n"
    "0x0136: GXC-MIPI-SC136CG, 0x8136: GXC-MIPI-SC136MG, 0x0235: GXC-MIPI-SC235CR。",
    "device_info", "read", "none", "0x0004"))

commands.append(cmd("sensorname", "Sensor Model", "传感器型号",
    "Read the sensor model name.\n"
    "0x662: IMX662-AAQR, 0x664: IMX664-AAQR1, 0x8234: AR0234CSSC,\n"
    "0xC002: GMAX4002-AVC, 0x8535: SC535HGS-C, 0x8136: SC136HGS-C,\n"
    "0x0285: SC285SL-C, 0x0485: SC485SL-C, 0x0235: SC235HAI.",
    "读取传感器型号名称。\n"
    "0x662: IMX662-AAQR, 0x664: IMX664-AAQR1, 0x8234: AR0234CSSC,\n"
    "0xC002: GMAX4002-AVC, 0x8535: SC535HGS-C, 0x8136: SC136HGS-C,\n"
    "0x0285: SC285SL-C, 0x0485: SC485SL-C, 0x0235: SC235HAI。",
    "device_info", "read", "none", "0x0008"))

commands.append(cmd("serialno", "Serial Number", "序列号",
    "Read the factory serial number.",
    "读取出厂序列号。",
    "device_info", "read", "none", "0x000C"))

commands.append(cmd("version", "Device Version", "设备版本",
    "Read firmware version. High 16 bits = Control version, Low 16 bits = Logic version.",
    "读取固件版本号。高16位 = 控制版本，低16位 = 逻辑版本。",
    "device_info", "read", "none", "0x0010"))

commands.append(cmd("timestamp", "Time Stamp", "时间戳",
    "Read time after system startup in milliseconds.",
    "读取系统启动后的时间（毫秒）。",
    "device_info", "read", "none", "0x0020"))

commands.append(cmd("errcode", "Error Code", "错误码",
    "Read the error code register (reserved).",
    "读取错误码寄存器（保留）。",
    "device_info", "read", "none", "0x0024"))

# ==================== B2. Capability Registers (Read-only) ====================
commands.append(cmd("fmtcap", "Format Capability", "格式能力",
    "Read data format capability bitmask. bit0=Mono8, bit1=Mono10, bit2=Mono12, bit4=UYVY, bit5=RGB888, bit7=YUYV.",
    "读取数据格式能力位掩码。bit0=Mono8, bit1=Mono10, bit2=Mono12, bit4=UYVY, bit5=RGB888, bit7=YUYV。",
    "capabilities", "read", "none", "0x0028"))

commands.append(cmd("readmodecap", "Read Mode Capability", "读取模式能力",
    "Read mode capability. bit0=Normal, bit1=Binning, bit2=Subsampling.",
    "读取模式能力。bit0=普通, bit1=Binning, bit2=Subsampling。",
    "capabilities", "read", "none", "0x002C"))

commands.append(cmd("workmodecap", "Work Mode Capability", "工作模式能力",
    "Read work/trigger mode capability. bit0=Video streaming, bit1=Normal trigger, bit3=Pulse trigger, bit4=Multi-camera sync.",
    "读取工作/触发模式能力。bit0=视频流, bit1=普通触发, bit3=脉冲触发, bit4=多机同步。",
    "capabilities", "read", "none", "0x0030"))

commands.append(cmd("lanecap", "Lane Capability", "Lane 能力",
    "Read supported MIPI lane count capability. e.g. 0x2=2 lanes, 0xA=2+4 lanes.",
    "读取支持的 MIPI Lane 数量能力。如 0x2=2 lanes, 0xA=2+4 lanes。",
    "capabilities", "read", "none", "0x0034"))

commands.append(cmd("videomodecap", "Video Mode Capability", "分辨率模式能力",
    "Read resolution mode capability. Bit0=ROI mode, Bit1=Preset Mode.",
    "读取分辨率模式能力。Bit0=ROI模式, Bit1=预设模式。",
    "capabilities", "read", "none", "0x005C"))

commands.append(cmd("videomodenum", "Resolution Mode Count", "分辨率模式数量",
    "Read the number of supported resolution modes (up to 8).",
    "读取支持的分辨率模式数量（最多8种）。",
    "capabilities", "read", "none", "0x0060"))

commands.append(cmd("maxwh", "Max Resolution", "最大分辨率",
    "Read sensor maximum width and height.",
    "读取传感器最大宽度和高度。",
    "capabilities", "read", "none", "0x0808",
    notes_en="Reads two registers: 0x0808 (width) and 0x080C (height).",
    notes_zh="读取两个寄存器：0x0808（宽度）和 0x080C（高度）。"))

commands.append(cmd("maxfps", "Max Frame Rate", "最大帧率",
    "Read maximum frame rate. Register value = fps * 100.",
    "读取最大帧率。寄存器值 = fps * 100。",
    "capabilities", "read", "none", "0x0810",
    value_transform={"read": "value / 100", "unit": "fps"}))

commands.append(cmd("minwh", "Min Resolution", "最小分辨率",
    "Read minimum supported ROI width and height.",
    "读取最小支持的 ROI 宽度和高度。",
    "capabilities", "read", "none", "0x0844",
    notes_en="Reads two registers: 0x0844 (width) and 0x0848 (height).",
    notes_zh="读取两个寄存器：0x0844（宽度）和 0x0848（高度）。"))

commands.append(cmd("minfps", "Min Frame Rate", "最小帧率",
    "Read minimum frame rate. Register value = fps * 10000.",
    "读取最小帧率。寄存器值 = fps * 10000。",
    "capabilities", "read", "none", "0x084C",
    value_transform={"read": "value / 10000", "unit": "fps"}))

# ==================== B3. Resolution & Framerate ====================
# --- RW commands (configuration) first ---
commands.append(cmd("videomode", "Resolution Mode", "分辨率模式",
    "Set/get resolution mode index [0-7] for cameras using preset resolution modes.",
    "设置/获取分辨率模式索引 [0-7]，用于使用预设分辨率模式的相机。",
    "video_modes", "rw", "medium", "0x082C",
    update_timing="S",
    cap_modes=[2],
    params=[int_param("Mode", "模式", "Resolution mode index", "分辨率模式索引", 0, 7)]))

commands.append(cmd("roi", "ROI Configuration", "ROI 配置",
    "Set/get Region of Interest (x offset, y offset, width, height). Step value: 8 pixels.",
    "设置/获取感兴趣区域（x 偏移, y 偏移, 宽度, 高度）。步进值：8 像素。",
    "video_modes", "rw", "medium", "0x0820",
    cap_modes=[1],
    params=[
        int_param("Offset X", "X 偏移", "ROI X offset", "ROI X 偏移", 0, 65535),
        int_param("Offset Y", "Y 偏移", "ROI Y 偏移", "ROI Y 偏移", 0, 65535),
        int_param("Width", "宽度", "ROI width", "ROI 宽度", 1, 65535),
        int_param("Height", "高度", "ROI height", "ROI 高度", 1, 65535)
    ],
    notes_en="Writes four registers: 0x0820 (X), 0x0824 (Y), 0x0818 (W), 0x081C (H).",
    notes_zh="写入四个寄存器：0x0820（X）、0x0824（Y）、0x0818（W）、0x081C（H）。"))

commands.append(cmd("fps_write", "Frame Rate", "帧率",
    "Set/get frame rate in fps. Register value = fps * 10000.",
    "设置/获取帧率（fps）。寄存器值 = fps * 10000。",
    "video_modes", "rw", "medium", "0x0850",
    update_timing="S",
    params=[float_param("FPS", "帧率", "Frame rate", "帧率", 0.0001, 120, 0.0001, unit="fps")],
    value_transform={"write": "value * 10000", "unit": "fps"}))

# --- RO commands (preset mode info) below ---
for i in range(1, 9):
    wh_reg = 0x0064 + (i - 1) * 8
    param_reg = 0x0068 + (i - 1) * 8
    commands.append(cmd(f"videomodewh{i}", f"Resolution Mode {i} W/H", f"分辨率模式 {i} 宽/高",
        f"Read resolution mode {i} resolution. Upper 16 bits = width, Lower 16 bits = height.",
        f"读取分辨率模式{i}的分辨率。高16位=宽度，低16位=高度。",
        "video_modes", "read", "none", f"0x{wh_reg:04X}", cap_modes=[2]))
    commands.append(cmd(f"videomodeparam{i}", f"Resolution Mode {i} Params", f"分辨率模式 {i} 参数",
        f"Read resolution mode {i} frame rate and read mode. Mid 8 bits = read mode (0=normal,1=binning,2=subsampling), Low 16 bits = frame rate.",
        f"读取分辨率模式{i}的帧率和读取方式。中间8位=读取方式(0=普通,1=binning,2=subsampling)，低16位=帧率。",
        "video_modes", "read", "none", f"0x{param_reg:04X}", cap_modes=[2]))

# ==================== B4. Current Status (Read-only) ====================
commands.append(cmd("curwh", "Current Resolution", "当前分辨率",
    "Read current ROI width and height. Registers 0x0818/0x081C are RW in ROI mode.",
    "读取当前 ROI 宽度和高度。寄存器 0x0818/0x081C 在 ROI 模式下可读写。",
    "current_status", "read", "none", "0x0818",
    notes_en="Reads two registers: 0x0818 (ROI Width) and 0x081C (ROI Height).",
    notes_zh="读取两个寄存器：0x0818（ROI 宽度）和 0x081C（ROI 高度）。"))

commands.append(cmd("mipidatarate", "MIPI Data Rate", "MIPI 数据率",
    "Read MIPI data rate per lane in kbps.",
    "读取每 Lane 的 MIPI 数据率（kbps）。",
    "current_status", "read", "none", "0x0840",
    value_transform={"unit": "kbps"}))

commands.append(cmd("fps", "Current Frame Rate", "当前帧率",
    "Read current frame rate. Register value = fps * 10000.",
    "读取当前帧率。寄存器值 = fps * 10000。",
    "current_status", "read", "none", "0x0850",
    value_transform={"read": "value / 10000", "unit": "fps"}))

commands.append(cmd("readmode", "Read Mode", "读取模式",
    "Read current read mode. 0=Normal, 1=2x2 Binning, 2=Subsampling.",
    "读取当前读取模式。0=普通, 1=2x2 Binning, 2=Subsampling。",
    "current_status", "read", "none", "0x0838"))

commands.append(cmd("lanenum", "Lane Number", "Lane 数量",
    "Read current MIPI lane count (2 or 4).",
    "读取当前 MIPI Lane 数量（2 或 4）。",
    "current_status", "read", "none", "0x083C"))

commands.append(cmd("framecount", "Frame Count", "帧计数",
    "Read sensor and output frame counts.",
    "读取传感器帧计数和输出帧计数。",
    "current_status", "read", "none", "0x0464",
    notes_en="Reads two registers: 0x0464 (sensor) and 0x0468 (output).",
    notes_zh="读取两个寄存器：0x0464（传感器）和 0x0468（输出）。"))

commands.append(cmd("sensortemp", "Sensor Temperature", "传感器温度",
    "Read sensor junction temperature in Kelvin. Register value = Kelvin * 100.",
    "读取传感器结温（开尔文）。寄存器值 = 开尔文 * 100。",
    "current_status", "read", "none", "0x0058",
    value_transform={"read": "value / 100", "unit": "K"}))

commands.append(cmd("isptemp", "ISP Temperature", "ISP 温度",
    "Read ISP chip junction temperature in Kelvin. Register value = Kelvin * 100.",
    "读取 ISP 芯片结温（开尔文）。寄存器值 = 开尔文 * 100。",
    "current_status", "read", "none", "0x00A4",
    value_transform={"read": "value / 100", "unit": "K"}))

# ==================== B5. Exposure & Gain ====================
# --- Current values (read-only) ---
commands.append(cmd("exptime", "Exposure Time", "曝光时间",
    "Read current exposure time in microseconds.",
    "读取当前曝光时间（微秒）。",
    "exposure_gain", "read", "none", "0x0C18",
    update_timing="R",
    value_transform={"unit": "μs"}))

commands.append(cmd("curgain", "Current Gain", "当前增益",
    "Read current gain value. Register value = dB * 10.",
    "读取当前增益值。寄存器值 = dB * 10。",
    "exposure_gain", "read", "none", "0x0C28",
    update_timing="R",
    value_transform={"read": "value / 10", "unit": "dB"}))

commands.append(cmd("cur_iso", "Current ISO", "当前 ISO",
    "Read current ISO value.",
    "读取当前 ISO 值。",
    "exposure_gain", "read", "none", "0x0CDC"))

# --- Auto exposure/gain configuration ---
commands.append(cmd("expmode", "Exposure Mode", "曝光模式",
    "Set/get exposure mode. 0=Manual, 2=Auto.",
    "设置/获取曝光模式。0=手动, 2=自动。",
    "exposure_gain", "rw", "low", "0x0C04",
    params=[enum_param("Mode", "模式", "Exposure mode", "曝光模式",
        [{"value": 0, "label": {"en": "Manual", "zh": "手动"}},
         {"value": 2, "label": {"en": "Auto", "zh": "自动"}}])]))

commands.append(cmd("aetarget", "AE Target Brightness", "AE 目标亮度",
    "Set/get target brightness for auto exposure. Range [0, 255].",
    "设置/获取自动曝光目标亮度。范围 [0, 255]。",
    "exposure_gain", "rw", "low", "0x0C08",
    params=[int_param("Target", "目标值", "Target brightness", "目标亮度", 0, 255)]))

commands.append(cmd("aestrategy", "AE Strategy", "AE 策略",
    "Set/get auto exposure strategy. 0=Highlight priority, 1=Shadow priority (Backlight Compensation).",
    "设置/获取自动曝光策略。0=高亮优先, 1=暗区优先（逆光补偿）。",
    "exposure_gain", "rw", "low", "0x0C0C",
    params=[enum_param("Strategy", "策略", "AE strategy", "AE策略",
        [{"value": 0, "label": {"en": "Highlight priority", "zh": "高亮优先"}},
         {"value": 1, "label": {"en": "Shadow priority", "zh": "暗区优先"}}])]))

commands.append(cmd("aemaxtime", "AE Max Exposure Time", "AE 最大曝光时间",
    "Set/get maximum exposure time in auto exposure mode. Range [16, 1000000] us.",
    "设置/获取自动曝光模式下的最大曝光时间。范围 [16, 1000000] 微秒。",
    "exposure_gain", "rw", "low", "0x0C14",
    params=[int_param("Max Time", "最大时间", "Max exposure time", "最大曝光时间", 16, 1000000, unit="μs")]))

commands.append(cmd("aemintime", "AE Min Exposure Time", "AE 最小曝光时间",
    "Set/get minimum exposure time in auto exposure mode. Range [16, 1000000] us.",
    "设置/获取自动曝光模式下的最小曝光时间。范围 [16, 1000000] 微秒。",
    "exposure_gain", "rw", "low", "0x0C5C",
    params=[int_param("Min Time", "最小时间", "Min exposure time", "最小曝光时间", 16, 1000000, unit="μs")]))

commands.append(cmd("aemaxgain", "AE Max Gain", "自动最大增益",
    "Set/get maximum gain in auto exposure mode. Register value = dB * 10.",
    "设置/获取自动曝光模式下的最大增益。寄存器值 = dB * 10。",
    "exposure_gain", "rw", "low", "0x0C24",
    params=[float_param("Max Gain", "最大增益", "Max gain value", "最大增益值", 0, 409.5, 0.1, unit="dB")],
    value_transform={"read": "value / 10", "write": "value * 10", "unit": "dB"}))

# --- Manual configuration ---
commands.append(cmd("metime", "Manual Exposure Time", "手动曝光时间",
    "Set/get manual exposure time in microseconds. Range [16, 1000000]. Only effective in manual mode.",
    "设置/获取手动曝光时间（微秒）。范围 [16, 1000000]。仅在手动模式下生效。",
    "exposure_gain", "rw", "low", "0x0C10",
    params=[int_param("Time", "时间", "Exposure time", "曝光时间", 16, 1000000, unit="μs")],
    notes_en="Unit: microseconds. Note: actual sensor precision is 1 line.",
    notes_zh="单位：微秒。注意：传感器实际精度为 1 line。"))

commands.append(cmd("mgain", "Manual Gain", "手动增益",
    "Set/get manual gain value. Register value = dB * 10. Only effective in manual gain mode (expmode=0).",
    "设置/获取手动增益值。寄存器值 = dB * 10。仅在手动增益模式（expmode=0）下生效。",
    "exposure_gain", "rw", "low", "0x0C20",
    params=[float_param("Gain", "增益", "Gain value", "增益值", 0, 409.5, 0.1, unit="dB")],
    value_transform={"read": "value / 10", "write": "value * 10", "unit": "dB"},
    notes_en="Register value is 10x the actual dB value. Range and step vary by sensor model.",
    notes_zh="寄存器值为实际 dB 值的 10 倍。范围和步进因型号而异。"))

# --- Exposure-related ISP settings ---
commands.append(cmd("antiflicker", "Anti-flicker", "防闪烁",
    "Set/get anti-flicker enable and frequency. Enable: 0=off, 1=on. Frequency: 50 or 60 Hz.",
    "设置/获取防闪烁使能和频率。使能：0=关, 1=开。频率：50 或 60 Hz。",
    "exposure_gain", "rw", "low", "0x0C94",
    params=[
        enum_param("Enable", "使能", "Anti-flicker enable", "防闪烁使能",
            [{"value": 0, "label": {"en": "Disable", "zh": "禁用"}},
             {"value": 1, "label": {"en": "Enable", "zh": "启用"}}]),
        enum_param("Frequency", "频率", "Anti-flicker frequency", "防闪烁频率",
            [{"value": 50, "label": {"en": "50 Hz", "zh": "50 Hz"}},
             {"value": 60, "label": {"en": "60 Hz", "zh": "60 Hz"}}])
    ],
    notes_en="Writes two registers: 0x0C94 (enable) and 0x0C98 (frequency).",
    notes_zh="写入两个寄存器：0x0C94（使能）和 0x0C98（频率）。"))

commands.append(cmd("slowshutter", "Slow Shutter", "慢快门",
    "Set/get slow shutter enable and gain threshold. Only effective in auto exposure + video stream mode. Gain threshold unit: 0.1 dB.",
    "设置/获取慢快门使能和增益阈值。仅在自动曝光 + 视频流模式下生效。增益阈值单位：0.1 dB。",
    "exposure_gain", "rw", "low", "0x0CBC",
    params=[
        enum_param("Enable", "使能", "Slow shutter enable", "慢快门使能",
            [{"value": 0, "label": {"en": "Disable", "zh": "禁用"}},
             {"value": 1, "label": {"en": "Enable", "zh": "启用"}}]),
        float_param("Gain Threshold", "增益阈值", "Gain threshold for auto frame reduction", "自动降帧增益阈值", 0, 409.5, 0.1, unit="dB")
    ],
    notes_en="Writes two registers: 0x0CBC (enable) and 0x0CC0 (gain threshold * 10). When using slow shutter, set aemaxtime=1000000 first.",
    notes_zh="写入两个寄存器：0x0CBC（使能）和 0x0CC0（增益阈值 * 10）。使用慢快门时需先设置 aemaxtime=1000000。"))

commands.append(cmd("aeweight", "AE Weight", "AE 区域权重",
    "Set/get AE region weighting. 0=Center-priority, 1=Bottom-priority, 2=Top-priority.",
    "设置/获取 AE 区域权重。0=中心优先, 1=底部优先, 2=顶部优先。",
    "exposure_gain", "rw", "low", "0x0CE0",
    params=[enum_param("Weight", "权重", "AE weight mode", "AE 权重模式",
        [{"value": 0, "label": {"en": "Center priority", "zh": "中心优先"}},
         {"value": 1, "label": {"en": "Bottom priority", "zh": "底部优先"}},
         {"value": 2, "label": {"en": "Top priority", "zh": "顶部优先"}}])]))

# ==================== B6. White Balance ====================
# --- Read-only current values first ---
commands.append(cmd("colortemp", "Color Temperature", "当前色温",
    "Read current color temperature in Kelvin.",
    "读取当前色温（开尔文）。",
    "white_balance", "read", "none", "0x0C50",
    update_timing="R",
    value_transform={"unit": "K"}))

commands.append(cmd("currgain", "Current R Gain", "当前 R 增益",
    "Read current white balance R gain [0, 4095].",
    "读取当前白平衡 R 增益 [0, 4095]。",
    "white_balance", "read", "none", "0x0C54",
    update_timing="R"))

commands.append(cmd("curbgain", "Current B Gain", "当前 B 增益",
    "Read current white balance B gain [0, 4095].",
    "读取当前白平衡 B 增益 [0, 4095]。",
    "white_balance", "read", "none", "0x0C58",
    update_timing="R"))

# --- RW configuration commands ---
commands.append(cmd("wbmode", "WB Mode", "白平衡模式",
    "Set/get white balance mode. 0=Manual, 2=Auto.",
    "设置/获取白平衡模式。0=手动, 2=自动。",
    "white_balance", "rw", "low", "0x0C3C",
    params=[enum_param("Mode", "模式", "WB mode", "白平衡模式",
        [{"value": 0, "label": {"en": "Manual", "zh": "手动"}},
         {"value": 2, "label": {"en": "Auto", "zh": "自动"}}])]))

commands.append(cmd("awbcolortempmin", "AWB Min Color Temp", "AWB 最小色温",
    "Set/get minimum color temperature for auto white balance. Range [1000, 15000] K.",
    "设置/获取自动白平衡最小色温。范围 [1000, 15000] K。",
    "white_balance", "rw", "low", "0x0C40",
    params=[int_param("Min Temp", "最小色温", "Min color temperature", "最小色温", 1000, 15000, unit="K")]))

commands.append(cmd("awbcolortempmax", "AWB Max Color Temp", "AWB 最大色温",
    "Set/get maximum color temperature for auto white balance. Range [1000, 15000] K.",
    "设置/获取自动白平衡最大色温。范围 [1000, 15000] K。",
    "white_balance", "rw", "low", "0x0C44",
    params=[int_param("Max Temp", "最大色温", "Max color temperature", "最大色温", 1000, 15000, unit="K")]))

commands.append(cmd("mwbrgain", "Manual WB R Gain", "手动白平衡 R 增益",
    "Set/get manual white balance R gain. Range [0, 4095].",
    "设置/获取手动白平衡 R 增益。范围 [0, 4095]。",
    "white_balance", "rw", "low", "0x0C48",
    params=[int_param("R Gain", "R 增益", "R gain value", "R 增益值", 0, 4095)]))

commands.append(cmd("mwbbgain", "Manual WB B Gain", "手动白平衡 B 增益",
    "Set/get manual white balance B gain. Range [0, 4095].",
    "设置/获取手动白平衡 B 增益。范围 [0, 4095]。",
    "white_balance", "rw", "low", "0x0C4C",
    params=[int_param("B Gain", "B 增益", "B gain value", "B 增益值", 0, 4095)]))

# ==================== B7. ISP Image Processing ====================
commands.append(cmd("gamma_index", "Gamma Selection", "Gamma 预设",
    "Set/get gamma preset. 0=Off(Linear), 1=Default, 2=Gamma1.6, 3=Gamma1.8, 4=Gamma2.0, 5=Gamma2.2, 6-11=Style1-6, 12=User-defined.",
    "设置/获取 Gamma 预设。0=关闭(线性), 1=默认, 2=Gamma1.6, 3=Gamma1.8, 4=Gamma2.0, 5=Gamma2.2, 6-11=风格1-6, 12=用户自定义。",
    "isp_processing", "rw", "low", "0x0CD0",
    params=[int_param("Gamma Index", "Gamma 索引", "Gamma preset index", "Gamma 预设索引", 0, 12)]))

commands.append(cmd("sharppen", "Sharpen Strength", "锐化强度",
    "Set/get sharpening strength. Range [0, 255].",
    "设置/获取锐化强度。范围 [0, 255]。",
    "isp_processing", "rw", "low", "0x0CA4",
    params=[int_param("Strength", "强度", "Sharpening strength", "锐化强度", 0, 255)]))

commands.append(cmd("denoise2d", "2D Denoise", "2D 降噪",
    "Set/get 2D noise reduction strength. Range [0, 255].",
    "设置/获取 2D 降噪强度。范围 [0, 255]。",
    "isp_processing", "rw", "low", "0x0CA8",
    params=[int_param("Strength", "强度", "2D denoise strength", "2D 降噪强度", 0, 255)]))

commands.append(cmd("denoise3d", "3D Denoise", "3D 降噪",
    "Set/get 3D noise reduction strength. Range [0, 255].",
    "设置/获取 3D 降噪强度。范围 [0, 255]。",
    "isp_processing", "rw", "low", "0x0CAC",
    params=[int_param("Strength", "强度", "3D denoise strength", "3D 降噪强度", 0, 255)]))

commands.append(cmd("saturation", "Saturation", "饱和度",
    "Set/get saturation. Range [0, 100].",
    "设置/获取饱和度。范围 [0, 100]。",
    "isp_processing", "rw", "low", "0x0CB0",
    params=[int_param("Saturation", "饱和度", "Saturation value", "饱和度值", 0, 100)]))

commands.append(cmd("contrast", "Contrast", "对比度",
    "Set/get contrast. Range [0, 100].",
    "设置/获取对比度。范围 [0, 100]。",
    "isp_processing", "rw", "low", "0x0CB4",
    params=[int_param("Contrast", "对比度", "Contrast value", "对比度值", 0, 100)]))

commands.append(cmd("hue", "Hue", "色调",
    "Set/get hue. Range [0, 100].",
    "设置/获取色调。范围 [0, 100]。",
    "isp_processing", "rw", "low", "0x0CB8",
    params=[int_param("Hue", "色调", "Hue value", "色调值", 0, 100)]))

commands.append(cmd("ldc", "Lens Distortion Correction", "镜头畸变校正",
    "Set/get LDC strength. Range [0, 255], 0=disable. Must be set before image acquisition to take effect.",
    "设置/获取 LDC 强度。范围 [0, 255]，0=禁用。需在相机采集图像前设置才能生效。",
    "isp_processing", "rw", "low", "0x0CC4",
    update_timing="S",
    params=[int_param("LDC", "LDC", "LDC strength", "LDC 强度", 0, 255)]))

commands.append(cmd("lsc", "Lens Shading Correction", "镜头阴影校正",
    "Set/get LSC (Mesh Lens Shading Correction) strength. Range [0, 255], 0=disable, 128=default.",
    "设置/获取 LSC（Mesh 镜头阴影校正）强度。范围 [0, 255]，0=禁用，128=默认。",
    "isp_processing", "rw", "low", "0x0CC8",
    params=[int_param("LSC", "LSC", "LSC strength", "LSC 强度", 0, 255)]))

commands.append(cmd("dehaze", "Dehaze Strength", "去雾强度",
    "Set/get dehaze (defogging) strength. Range [0, 255], 0=off.",
    "设置/获取去雾强度。范围 [0, 255]，0=关闭。",
    "isp_processing", "rw", "low", "0x0CCC",
    params=[int_param("Strength", "强度", "Dehaze strength", "去雾强度", 0, 255)]))

commands.append(cmd("drc", "DRC Strength", "DRC 强度",
    "Set/get digital wide dynamic range (DRC) strength. Range [0, 255], 0=off.",
    "设置/获取数字宽动态范围（DRC）强度。范围 [0, 255]，0=关闭。",
    "isp_processing", "rw", "low", "0x0CD4",
    params=[int_param("Strength", "强度", "DRC strength", "DRC 强度", 0, 255)]))

commands.append(cmd("wdrparam", "WDR Parameters", "WDR 参数",
    "Set/get WDR option and strength. Option: 0=Disable, 1=Digital WDR, 2=DOL WDR, 3=Clear WDR. Strength: [0, 255].",
    "设置/获取 WDR 选项和强度。选项：0=禁用, 1=数字WDR, 2=DOL WDR, 3=清晰WDR。强度：[0, 255]。",
    "isp_processing", "rw", "low", "0x0C9C",
    params=[
        enum_param("WDR Option", "WDR 选项", "WDR option", "WDR 选项",
            [{"value": 0, "label": {"en": "Disable", "zh": "禁用"}},
             {"value": 1, "label": {"en": "Digital WDR", "zh": "数字 WDR"}},
             {"value": 2, "label": {"en": "DOL WDR", "zh": "DOL WDR"}},
             {"value": 3, "label": {"en": "Clear WDR", "zh": "清晰 WDR"}}]),
        int_param("Strength", "强度", "WDR strength", "WDR 强度", 0, 255)
    ],
    notes_en="Writes two registers: 0x0C9C (option) and 0x0CA0 (strength).",
    notes_zh="写入两个寄存器：0x0C9C（选项）和 0x0CA0（强度）。"))

commands.append(cmd("scene_custom", "Scene Custom", "自定义场景",
    "Set/get custom scene selection. When bit 15 = 1, custom scene mode is enabled; otherwise auto selection.",
    "设置/获取自定义场景选择。当 bit 15 = 1 时启用自定义场景模式，否则自动选择。",
    "isp_processing", "rw", "low", "0x0CD8",
    params=[int_param("Scene", "场景", "Custom scene value", "自定义场景值", 0, 65535)]))

# ==================== B8. Trigger & Synchronization ====================
commands.append(cmd("workmode", "Work Mode", "工作模式",
    "Set/get work mode. 0=Video streaming, 1=Trigger, 3=Pulse trigger (hardware only), 4=Multi-camera sync. Requires stopping acquisition first.",
    "设置/获取工作模式。0=视频流, 1=触发, 3=脉冲触发(仅硬件), 4=多机同步。需先停止采集。",
    "trigger_sync", "rw", "medium", "0x0404",
    update_timing="S",
    params=[enum_param("Mode", "模式", "Work mode", "工作模式",
        [{"value": 0, "label": {"en": "Video Streaming", "zh": "视频流"}},
         {"value": 1, "label": {"en": "Trigger", "zh": "触发"}},
         {"value": 3, "label": {"en": "Pulse Trigger", "zh": "脉冲触发"}},
         {"value": 4, "label": {"en": "Multi-camera Sync", "zh": "多机同步"}}])]))

commands.append(cmd("trgsrc", "Trigger Source", "触发源",
    "Set/get trigger source. 0=Software trigger, 1=Hardware trigger. Effective in Work Mode 1 and 3 only.",
    "设置/获取触发源。0=软触发, 1=硬触发。仅在工作模式 1 和 3 下生效。",
    "trigger_sync", "rw", "low", "0x0408",
    params=[enum_param("Source", "触发源", "Trigger source", "触发源",
        [{"value": 0, "label": {"en": "Software", "zh": "软触发"}},
         {"value": 1, "label": {"en": "Hardware", "zh": "硬触发"}}])]))

commands.append(cmd("trgnum", "Trigger Number", "触发帧数",
    "Set/get number of trigger frames per trigger event. Range [1, 255], default 1.",
    "设置/获取每次触发的帧数。范围 [1, 255]，默认 1。",
    "trigger_sync", "rw", "low", "0x040C",
    params=[int_param("Number", "帧数", "Trigger frame count", "触发帧数", 1, 255, default=1)]))

commands.append(cmd("trginterval", "Trigger Interval", "触发间隔",
    "Set/get trigger interval in microseconds. Range [0, 0x00FFFFFF].",
    "设置/获取触发间隔（微秒）。范围 [0, 0x00FFFFFF]。",
    "trigger_sync", "rw", "low", "0x0410",
    params=[int_param("Interval", "间隔", "Trigger interval", "触发间隔", 0, 16777215, unit="μs")]))

commands.append(cmd("trgone", "Software Trigger", "软件触发",
    "Write 1 to trigger one frame capture. No parameters needed.",
    "写 1 触发一帧采集。无需参数。",
    "trigger_sync", "write", "medium", "0x0414",
    update_timing="S"))

commands.append(cmd("trgcount", "Trigger Count", "触发计数",
    "Read trigger statistics (success/lost counts). Write 1 to clear count.",
    "读取触发统计（成功/丢失计数）。写 1 清除计数。",
    "trigger_sync", "rw", "low", "0x0418",
    update_timing="S",
    params=[int_param("Clear", "清除", "Write 1 to clear", "写 1 清除", 1, 1)]))

commands.append(cmd("trgedge", "Trigger Edge", "触发边沿",
    "Set/get trigger edge polarity. 0=Rising edge, 1=Falling edge.",
    "设置/获取触发边沿极性。0=上升沿, 1=下降沿。",
    "trigger_sync", "rw", "low", "0x1004",
    update_timing="S",
    params=[enum_param("Edge", "边沿", "Trigger edge", "触发边沿",
        [{"value": 0, "label": {"en": "Rising", "zh": "上升沿"}},
         {"value": 1, "label": {"en": "Falling", "zh": "下降沿"}}])]))

commands.append(cmd("trgdelay", "Trigger Delay", "触发延迟",
    "Set/get trigger delay in microseconds. Range [0, 1000000]. Effective in both soft and hard trigger modes.",
    "设置/获取触发延迟（微秒）。范围 [0, 1000000]。在软触发和硬触发模式下均生效。",
    "trigger_sync", "rw", "low", "0x1000",
    update_timing="S",
    params=[int_param("Delay", "延迟", "Trigger delay", "触发延迟", 0, 1000000, unit="μs")]))

commands.append(cmd("trgexp_delay", "Exposure Delay", "曝光延迟",
    "Set/get exposure delay (strobe advance time) in microseconds. Range [0, 1000000].",
    "设置/获取曝光延迟（闪光灯提前时间）（微秒）。范围 [0, 1000000]。",
    "trigger_sync", "rw", "low", "0x1010",
    update_timing="S",
    params=[int_param("Delay", "延迟", "Exposure delay", "曝光延迟", 0, 1000000, unit="μs")]))

commands.append(cmd("slavemode", "Slave Mode", "从模式",
    "Set/get master/slave role in multi-camera sync mode. 0=Main Mode, 1=Slave Mode.",
    "设置/获取多机同步模式下的主从角色。0=主机模式, 1=从机模式。",
    "trigger_sync", "rw", "medium", "0x0460",
    update_timing="S",
    params=[enum_param("Role", "角色", "Master/Slave role", "主从角色",
        [{"value": 0, "label": {"en": "Master", "zh": "主机"}},
         {"value": 1, "label": {"en": "Slave", "zh": "从机"}}])]))

commands.append(cmd("triggercyclemin", "Min Trigger Cycle", "最小触发周期",
    "Read minimum trigger signal period in microseconds.",
    "读取最小触发信号周期（微秒）。",
    "trigger_sync", "read", "none", "0x046C",
    value_transform={"unit": "μs"}))

# ==================== B9. Day/Night & IRCUT ====================
commands.append(cmd("daynightmode", "Day/Night Mode", "日夜模式",
    "Set/get day/night mode. 0=Color, 1=B&W, 2=External Trigger.",
    "设置/获取日夜模式。0=彩色, 1=黑白, 2=外部触发。",
    "day_night", "rw", "low", "0x0474",
    params=[enum_param("Mode", "模式", "Day/Night mode", "日夜模式",
        [{"value": 0, "label": {"en": "Color", "zh": "彩色"}},
         {"value": 1, "label": {"en": "B&W", "zh": "黑白"}},
         {"value": 2, "label": {"en": "External Trigger", "zh": "外部触发"}}])]))

commands.append(cmd("ircutdir", "IRCUT Direction", "IRCUT 方向",
    "Set/get IRCUT direction reversal.",
    "设置/获取 IRCUT 方向反转。",
    "day_night", "rw", "low", "0x0478",
    params=[int_param("Direction", "方向", "IRCUT direction", "IRCUT 方向", 0, 1)]))

commands.append(cmd("pinpolarity", "Pin Polarity", "引脚极性",
    "Set/get day/night trigger pin polarity. Default: low level = night. Set 1: high level = night.",
    "设置/获取日夜触发引脚极性。默认：低电平=夜间。设为 1：高电平=夜间。",
    "day_night", "rw", "low", "0x047C",
    params=[int_param("Polarity", "极性", "Pin polarity", "引脚极性", 0, 1)]))

commands.append(cmd("ircuttimer", "IRCUT Timer", "IRCUT 定时器",
    "Set/get IRCUT periodic control enable. When enabled, IRCUT switches periodically.",
    "设置/获取 IRCUT 周期控制使能。启用后 IRCUT 按周期切换。",
    "day_night", "rw", "low", "0x0480",
    params=[int_param("Timer", "定时器", "IRCUT timer enable", "IRCUT 定时器使能", 0, 1)]))

# ==================== B10. GPIO Control ====================
commands.append(cmd("outio1_mode", "GPIO1 Output Mode", "GPIO1 输出模式",
    "Set/get GPIO1 output select. 0=Strobe, 1=UserOut, 2=TriggerWait (busy inverse).",
    "设置/获取 GPIO1 输出选择。0=Strobe, 1=UserOut, 2=TriggerWait（busy 反相）。",
    "gpio_control", "rw", "low", "0x1020",
    params=[enum_param("Mode", "模式", "GPIO1 output mode", "GPIO1 输出模式",
        [{"value": 0, "label": {"en": "Strobe", "zh": "Strobe"}},
         {"value": 1, "label": {"en": "UserOut", "zh": "UserOut"}},
         {"value": 2, "label": {"en": "TriggerWait", "zh": "TriggerWait"}}])]))

commands.append(cmd("outio1_rvs", "GPIO1 Reverse", "GPIO1 反转",
    "Set/get GPIO1 signal reversal.",
    "设置/获取 GPIO1 信号反转。",
    "gpio_control", "rw", "low", "0x1028",
    params=[int_param("Reverse", "反转", "Signal reverse", "信号反转", 0, 1)]))

# ==================== B11. Video & Format ====================
commands.append(cmd("testimg", "Test Image", "测试图像",
    "Set/get test image selector. 0=Off, 1=Vertical color bars.",
    "设置/获取测试图像选择。0=关闭, 1=竖彩色条纹。",
    "video_format", "rw", "low", "0x0800",
    params=[int_param("Selector", "选择", "Test image selector", "测试图像选择", 0, 1)]))

commands.append(cmd("pixelformat", "Pixel Format", "像素格式",
    "Set/get pixel format. 0=Mono8, 1=Mono10, 2=Mono12, 4=UYVY, 5=RGB888, 7=YUYV. Requires stopping acquisition.",
    "设置/获取像素格式。0=Mono8, 1=Mono10, 2=Mono12, 4=UYVY, 5=RGB888, 7=YUYV。需停止采集。",
    "video_format", "rw", "medium", "0x0804",
    update_timing="S",
    params=[enum_param("Format", "格式", "Pixel format", "像素格式",
        [{"value": 0, "label": "Mono8"}, {"value": 1, "label": "Mono10"},
         {"value": 2, "label": "Mono12"}, {"value": 4, "label": "UYVY"},
         {"value": 5, "label": "RGB888"}, {"value": 7, "label": "YUYV"}])]))

commands.append(cmd("imgdir", "Image Direction", "图像方向",
    "Set/get image orientation. 0=Normal, 1=Mirror, 2=Flip, 3=Flip+Mirror.",
    "设置/获取图像方向。0=正常, 1=镜像, 2=翻转, 3=翻转+镜像。",
    "video_format", "rw", "low", "0x0828",
    params=[enum_param("Direction", "方向", "Image direction", "图像方向",
        [{"value": 0, "label": {"en": "Normal", "zh": "正常"}},
         {"value": 1, "label": {"en": "Mirror", "zh": "镜像"}},
         {"value": 2, "label": {"en": "Flip", "zh": "翻转"}},
         {"value": 3, "label": {"en": "Flip+Mirror", "zh": "翻转+镜像"}}])]))

commands.append(cmd("nondiscontinuousmode", "MIPI Clock Mode", "MIPI 时钟模式",
    "Set/get MIPI clock mode. 0=Discontinuous, 1=Continuous.",
    "设置/获取 MIPI 时钟模式。0=非连续, 1=连续。",
    "video_format", "rw", "low", "0x044C",
    params=[enum_param("Mode", "模式", "Clock mode", "时钟模式",
        [{"value": 0, "label": {"en": "Discontinuous", "zh": "非连续"}},
         {"value": 1, "label": {"en": "Continuous", "zh": "连续"}}])]))

commands.append(cmd("metadata_mode", "Metadata Mode", "元数据模式",
    "Set/get metadata mode. 0=Disabled, 1=Overlay on image (last 64 Y pixels), 2=Footer Row Metadata (2 extra lines), 3=Embedded Line.",
    "设置/获取元数据模式。0=禁用, 1=叠加在图像上(最后64行Y像素), 2=底行元数据(追加2行), 3=嵌入式行。",
    "video_format", "rw", "low", "0x0858",
    params=[enum_param("Mode", "模式", "Metadata mode", "元数据模式",
        [{"value": 0, "label": {"en": "Disabled", "zh": "禁用"}},
         {"value": 1, "label": {"en": "Overlay on image", "zh": "叠加在图像上"}},
         {"value": 2, "label": {"en": "Footer Row Metadata", "zh": "底行元数据"}},
         {"value": 3, "label": {"en": "Embedded Line", "zh": "嵌入式行"}}])]))

# ==================== B12. System Control (High Risk) ====================
commands.append(cmd("imgacq", "Image Acquisition", "图像采集",
    "Start/stop image acquisition. 0=Stop, 1=Start.",
    "启动/停止图像采集。0=停止, 1=启动。",
    "system_control", "write", "medium", "0x0400",
    params=[enum_param("Acquisition", "采集", "Image acquisition", "图像采集",
        [{"value": 0, "label": {"en": "Stop", "zh": "停止"}},
         {"value": 1, "label": {"en": "Start", "zh": "启动"}}])]))

commands.append(cmd("factoryparam", "Factory Reset", "恢复出厂设置",
    "Restore all parameters to factory defaults. WARNING: This erases flash and rewrites. Do not interrupt power.",
    "恢复所有参数为出厂默认值。警告：此操作将擦除 Flash 并重写，请勿断电。",
    "system_control", "write", "high", "0x0014",
    requires_confirm=True))

commands.append(cmd("paramsave", "Save to Flash", "保存到 Flash",
    "Save all parameters to flash (non-volatile). WARNING: Do not interrupt power during operation.",
    "将所有参数保存到 Flash（非易失）。警告：操作过程中请勿断电。",
    "system_control", "write", "high", "0x0018",
    requires_confirm=True))

commands.append(cmd("reboot", "Reboot Camera", "重启相机",
    "Reboot the camera system. WARNING: Active configuration will be lost if not saved.",
    "重启相机系统。警告：如未保存，当前配置将丢失。",
    "system_control", "write", "high", "0x001C",
    requires_confirm=True))

commands.append(cmd("i2caddr", "I2C Address", "I2C 地址",
    "Set/get I2C address. Range [0x03, 0x77]. WARNING: Incorrect address will cause communication loss.",
    "设置/获取 I2C 地址。范围 [0x03, 0x77]。警告：错误地址将导致通信丢失。",
    "system_control", "rw", "high", "0x041C",
    requires_confirm=True,
    params=[int_param("Address", "地址", "I2C address (hex)", "I2C 地址（十六进制）", 3, 119)],
    notes_en="Default address is 0x3b. Changing to invalid address will cause communication loss.",
    notes_zh="默认地址为 0x3b。更改为无效地址将导致通信丢失。"))

# ==================== B13. Advanced Debug ====================
commands.append(cmd("redriver", "MIPI ReDriver", "MIPI ReDriver",
    "Set/get MIPI repeater register. Bit[0-3]=EQ[0-3], Bit[8-10]=ERC[0-3], Bit[16-19]=Output Pre-emphasis & Swing[0-3].",
    "设置/获取 MIPI 中继寄存器。Bit[0-3]=EQ[0-3], Bit[8-10]=ERC[0-3], Bit[16-19]=输出预加重&摆幅[0-3]。",
    "advanced", "rw", "medium", "0x048C",
    params=[int_param("Value", "值", "ReDriver register value", "ReDriver 寄存器值", 0, 0xFFFFF)]))

commands.append(cmd("snsreg", "Sensor Register Read", "传感器寄存器读取",
    "Read a raw sensor register value directly. Requires sensor register address parameter.",
    "直接读取传感器原始寄存器值。需要传感器寄存器地址参数。",
    "advanced", "read", "medium",
    reg_type="sensor",
    params=[int_param("Register Address", "寄存器地址", "Sensor register address (hex)", "传感器寄存器地址（十六进制）", 0, 0xFFFF)]))

# Build final JSON
output = {"commands": commands}

script_dir = os.path.dirname(os.path.abspath(__file__))
outpath = os.path.join(script_dir, "..", "config", "commands.json")
with open(outpath, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f"Generated {len(commands)} commands -> {outpath}")
