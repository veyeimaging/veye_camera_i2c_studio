#!/usr/bin/env python3
"""Patch commands.json to add execution_steps for direct i2c_vread/i2c_vwrite calls.

Execution step format:
  {"op": "read",  "reg": "0x0C18", "reg_type": 0}
  {"op": "write", "reg": "0x0C04", "reg_type": 0, "value_expr": "{param0}"}

reg_type: 0 = ARM register, 1 = sensor register
value_expr: Python expression; {param0}, {param1}... are user params,
            {read0}, {read1}... are previously read values.
"""
import json, os

CONFIG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")

def R(reg, rt=0):
    return {"op": "read", "reg": reg, "reg_type": rt}

def W(reg, expr, rt=0):
    return {"op": "write", "reg": reg, "reg_type": rt, "value_expr": expr}

def build_steps_map():
    """Build a dict: command_id -> execution_steps list."""
    s = {}

    # ---- Device Information (read-only) ----
    s["manufacturer"] = [R("0x0000")]
    s["model"]        = [R("0x0004")]
    s["sensorname"]   = [R("0x0008")]
    s["serialno"]     = [R("0x000C")]
    s["version"]      = [R("0x0010")]
    s["timestamp"]    = [R("0x0020")]
    s["errcode"]      = [R("0x0024")]

    # ---- Capabilities (read-only) ----
    s["fmtcap"]       = [R("0x0028")]
    s["readmodecap"]  = [R("0x002C")]
    s["workmodecap"]  = [R("0x0030")]
    s["lanecap"]      = [R("0x0034")]
    s["videomodecap"] = [R("0x005C")]
    s["videomodenum"] = [R("0x0060")]

    # ---- Video Mode Details (read-only, 8 groups of 2) ----
    wh_regs    = ["0x0064","0x006C","0x0074","0x007C","0x0084","0x008C","0x0094","0x009C"]
    param_regs = ["0x0068","0x0070","0x0078","0x0080","0x0088","0x0090","0x0098","0x00A0"]
    for i in range(8):
        s[f"videomodewh{i+1}"]    = [R(wh_regs[i])]
        s[f"videomodeparam{i+1}"] = [R(param_regs[i])]

    # ---- Current Status (read-only, some multi-register) ----
    s["maxwh"]           = [R("0x0808"), R("0x080C")]
    s["maxfps"]          = [R("0x0810")]
    s["curwh"]           = [R("0x0818"), R("0x081C")]
    s["minwh"]           = [R("0x0844"), R("0x0848")]
    s["mipidatarate"]    = [R("0x0840")]
    s["minfps"]          = [R("0x084C")]
    s["fps"]             = [R("0x0850")]
    s["readmode"]        = [R("0x0838")]
    s["lanenum"]         = [R("0x083C")]
    s["exptime"]         = [R("0x0C18")]
    s["curgain"]         = [R("0x0C28")]
    s["colortemp"]       = [R("0x0C50")]
    s["currgain"]        = [R("0x0C54")]
    s["curbgain"]        = [R("0x0C58")]
    s["cur_iso"]         = [R("0x0CDC")]
    s["framecount"]      = [R("0x0464"), R("0x0468")]
    s["triggercyclemin"] = [R("0x046C")]
    s["sensortemp"]      = [R("0x0058")]
    s["isptemp"]         = [R("0x00A4")]

    # ---- Exposure & Gain (RW) ----
    s["expmode"]    = [R("0x0C04"), W("0x0C04", "{param0}")]
    s["aetarget"]   = [R("0x0C08"), W("0x0C08", "{param0}")]
    s["aestrategy"] = [R("0x0C0C"), W("0x0C0C", "{param0}")]
    s["metime"]     = [R("0x0C10"), W("0x0C10", "{param0}")]
    s["aemaxtime"]  = [R("0x0C14"), W("0x0C14", "{param0}")]
    s["aemintime"]  = [R("0x0C5C"), W("0x0C5C", "{param0}")]
    s["mgain"]      = [R("0x0C20"), W("0x0C20", "int(round({param0} * 10))")]
    s["aemaxgain"]  = [R("0x0C24"), W("0x0C24", "int(round({param0} * 10))")]

    # ---- White Balance (RW) ----
    s["wbmode"]          = [R("0x0C3C"), W("0x0C3C", "{param0}")]
    s["awbcolortempmin"] = [R("0x0C40"), W("0x0C40", "{param0}")]
    s["awbcolortempmax"] = [R("0x0C44"), W("0x0C44", "{param0}")]
    s["mwbrgain"]        = [R("0x0C48"), W("0x0C48", "{param0}")]
    s["mwbbgain"]        = [R("0x0C4C"), W("0x0C4C", "{param0}")]

    # ---- ISP Image Processing (RW) ----
    s["gamma_index"] = [R("0x0CD0"), W("0x0CD0", "{param0}")]
    s["sharppen"]    = [R("0x0CA4"), W("0x0CA4", "{param0}")]
    s["denoise2d"]   = [R("0x0CA8"), W("0x0CA8", "{param0}")]
    s["denoise3d"]   = [R("0x0CAC"), W("0x0CAC", "{param0}")]
    s["saturation"]  = [R("0x0CB0"), W("0x0CB0", "{param0}")]
    s["contrast"]    = [R("0x0CB4"), W("0x0CB4", "{param0}")]
    s["hue"]         = [R("0x0CB8"), W("0x0CB8", "{param0}")]
    s["ldc"]         = [R("0x0CC4"), W("0x0CC4", "{param0}")]
    s["lsc"]         = [R("0x0CC8"), W("0x0CC8", "{param0}")]
    s["dehaze"]      = [R("0x0CCC"), W("0x0CCC", "{param0}")]
    s["drc"]         = [R("0x0CD4"), W("0x0CD4", "{param0}")]
    # Multi-register: wdrparam (enable + strength)
    s["wdrparam"]    = [R("0x0C9C"), R("0x0CA0"),
                        W("0x0C9C", "{param0}"), W("0x0CA0", "{param1}")]
    # Multi-register: antiflicker (enable + freq)
    s["antiflicker"] = [R("0x0C94"), R("0x0C98"),
                        W("0x0C94", "{param0}"), W("0x0C98", "{param1}")]
    # Multi-register: slowshutter (enable + gain_threshold*10)
    s["slowshutter"] = [R("0x0CBC"), R("0x0CC0"),
                        W("0x0CBC", "{param0}"), W("0x0CC0", "int(round({param1} * 10))")]
    s["aeweight"]    = [R("0x0CE0"), W("0x0CE0", "{param0}")]
    s["scene_custom"]= [R("0x0CD8"), W("0x0CD8", "{param0}")]

    # ---- Trigger & Synchronization ----
    s["workmode"]      = [R("0x0404"), W("0x0404", "{param0}")]
    s["trgsrc"]        = [R("0x0408"), W("0x0408", "{param0}")]
    s["trgnum"]        = [R("0x040C"), W("0x040C", "{param0}")]
    s["trginterval"]   = [R("0x0410"), W("0x0410", "{param0}")]
    s["trgone"]        = [W("0x0414", "1")]
    s["trgcount"]      = [R("0x0418"), W("0x0418", "1")]
    s["trgedge"]       = [R("0x1004"), W("0x1004", "{param0}")]
    s["trgdelay"]      = [R("0x1000"), W("0x1000", "{param0}")]
    s["trgexp_delay"]  = [R("0x1010"), W("0x1010", "{param0}")]

    # ---- Day/Night & IRCUT ----
    s["daynightmode"]  = [R("0x0474"), W("0x0474", "{param0}")]
    s["ircutdir"]      = [R("0x0478"), W("0x0478", "{param0}")]
    s["pinpolarity"]   = [R("0x047C"), W("0x047C", "{param0}")]
    s["ircuttimer"]    = [R("0x0480"), W("0x0480", "{param0}")]

    # ---- GPIO Control ----
    s["outio1_mode"]   = [R("0x1020"), W("0x1020", "{param0}")]
    s["outio1_rvs"]    = [R("0x1028"), W("0x1028", "{param0}")]

    # ---- Video & Format ----
    s["testimg"]              = [R("0x0800"), W("0x0800", "{param0}")]
    s["pixelformat"]          = [R("0x0804"), W("0x0804", "{param0}")]
    s["imgdir"]               = [R("0x0828"), W("0x0828", "{param0}")]
    s["videomode"]            = [R("0x082C"), W("0x082C", "{param0}")]
    s["nondiscontinuousmode"] = [R("0x044C"), W("0x044C", "{param0}")]
    s["metadata_mode"]        = [R("0x0858"), W("0x0858", "{param0}")]

    # ---- System Control ----
    s["imgacq"]        = [W("0x0400", "{param0}")]
    s["factoryparam"]  = [W("0x0014", "1")]
    s["paramsave"]     = [W("0x0018", "1")]
    s["reboot"]        = [W("0x001C", "1")]
    s["i2caddr"]       = [R("0x041C"), W("0x041C", "{param0}")]
    s["slavemode"]     = [R("0x0460"), W("0x0460", "{param0}")]

    # ---- Advanced Debug ----
    s["redriver"]   = [R("0x048C"), W("0x048C", "{param0}")]
    # snsreg: reads SENSOR register (reg_type=1), address from param0
    s["snsreg"]     = [R("{param0}", 1)]
    # roi: 4 registers (offset_x, offset_y, width, height)
    s["roi"]        = [R("0x0820"), R("0x0824"), R("0x0818"), R("0x081C"),
                       W("0x0820", "{param0}"), W("0x0824", "{param1}"),
                       W("0x0818", "{param2}"), W("0x081C", "{param3}")]
    # fps_write: read + write (value * 10000)
    s["fps_write"]  = [R("0x0850"), W("0x0850", "int(round({param0} * 10000))")]

    return s


def main():
    cmds_path = os.path.join(CONFIG_DIR, "commands.json")
    with open(cmds_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    steps_map = build_steps_map()
    patched = 0
    missing = []

    for cmd in data.get("commands", []):
        cid = cmd["id"]
        if cid in steps_map:
            cmd["execution_steps"] = steps_map[cid]
            patched += 1
        else:
            missing.append(cid)

    with open(cmds_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"Patched {patched} commands with execution_steps")
    if missing:
        print(f"WARNING: {len(missing)} commands missing from steps map: {missing}")


if __name__ == "__main__":
    main()
