#!/usr/bin/env python3
"""
Script to extract script function mappings from i2c_functions.sh
and update commands.json with script_functions field.

Usage:
    python3 scripts/update_script_functions.py

This script:
1. Parses gx_i2c_tools/i2c_functions.sh to extract register variable definitions
2. Parses function definitions and their register usage
3. Builds a mapping from register address to script function names
4. Updates config/commands.json with the script_functions field
"""

import re
import json
import os
import sys

# Paths relative to project root
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
I2C_FUNCTIONS_SH = os.path.join(PROJECT_ROOT, '..', 'gx_i2c_tools', 'i2c_functions.sh')
COMMANDS_JSON = os.path.join(PROJECT_ROOT, 'config', 'commands.json')


def parse_register_variables(content: str) -> dict:
    """Extract register variable definitions like 'FrameRate_Ex=0x850;'"""
    reg_vars = {}
    for match in re.finditer(r'^(\w+)=0x([0-9A-Fa-f]+);', content, re.MULTILINE):
        var_name = match.group(1)
        # Normalize to 4-digit hex with 0x prefix
        reg_addr = '0x' + match.group(2).upper().zfill(4)
        reg_vars[var_name] = reg_addr
    return reg_vars


def parse_functions(content: str) -> dict:
    """
    Parse function definitions and extract register usage.
    Returns dict: {func_name: var_name}
    """
    functions = {}
    lines = content.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i].strip()
        # Check for function definition: funcname() { or funcname () {
        match = re.match(r'^(\w+)\s*\(\s*\)\s*\{?$', line)
        if match:
            func_name = match.group(1)
            
            # Find the opening brace if not on same line
            if '{' not in line:
                i += 1
                while i < len(lines) and '{' not in lines[i]:
                    i += 1
            
            # Find the matching closing brace (handle nested braces)
            brace_count = 0
            func_body_lines = []
            started = False
            
            while i < len(lines):
                for char in lines[i]:
                    if char == '{':
                        brace_count += 1
                        started = True
                    elif char == '}':
                        brace_count -= 1
                
                if started:
                    func_body_lines.append(lines[i])
                
                if started and brace_count == 0:
                    break
                i += 1
            
            func_body = '\n'.join(func_body_lines)
            
            # Find register usage: i2c_read $VarName, i2c_write $VarName, etc.
            reg_usage = re.findall(r'i2c_(?:read|write|readsensor)\s+\$(\w+)', func_body)
            if reg_usage:
                functions[func_name] = reg_usage[0]  # First register used
        
        i += 1
    
    return functions


def strip_prefix(func_name: str) -> str:
    """Remove read_ or write_ prefix from function name."""
    if func_name.startswith('read_'):
        return func_name[5:]
    elif func_name.startswith('write_'):
        return func_name[6:]
    return func_name


def build_reg_to_funcs_map(reg_vars: dict, functions: dict) -> dict:
    """Build reverse mapping: register address -> list of function base names (without read_/write_ prefix)"""
    reg_to_funcs = {}
    for func_name, var_name in functions.items():
        addr = reg_vars.get(var_name)
        if addr:
            base_name = strip_prefix(func_name)
            if addr not in reg_to_funcs:
                reg_to_funcs[addr] = set()
            reg_to_funcs[addr].add(base_name)
    # Convert sets to sorted lists
    for addr in reg_to_funcs:
        reg_to_funcs[addr] = sorted(reg_to_funcs[addr])
    return reg_to_funcs


def normalize_address(addr: str) -> str:
    """Normalize register address to 0xXXXX format (4-digit uppercase hex)"""
    normalized = addr.upper()
    if not normalized.startswith('0X'):
        normalized = '0x' + normalized
    hex_part = normalized[2:]
    return '0x' + hex_part.zfill(4)


def update_commands_json(commands_path: str, reg_to_funcs: dict) -> int:
    """Update commands.json with script_functions field. Returns count of updated commands."""
    with open(commands_path, 'r') as f:
        commands_data = json.load(f)
    
    updated_count = 0
    for cmd in commands_data.get('commands', []):
        reg = cmd.get('register')
        if reg and isinstance(reg, dict):
            reg_addr = reg.get('address')
            if reg_addr:
                normalized = normalize_address(reg_addr)
                funcs = reg_to_funcs.get(normalized, [])
                if funcs:
                    cmd['script_functions'] = funcs
                    updated_count += 1
                elif 'script_functions' in cmd:
                    # Remove if no functions found
                    del cmd['script_functions']
    
    with open(commands_path, 'w') as f:
        json.dump(commands_data, f, indent=2, ensure_ascii=False)
    
    return updated_count


def main():
    print(f"Parsing {I2C_FUNCTIONS_SH}...")
    
    if not os.path.exists(I2C_FUNCTIONS_SH):
        print(f"Error: {I2C_FUNCTIONS_SH} not found")
        sys.exit(1)
    
    with open(I2C_FUNCTIONS_SH, 'r') as f:
        content = f.read()
    
    reg_vars = parse_register_variables(content)
    print(f"  Found {len(reg_vars)} register variables")
    
    functions = parse_functions(content)
    print(f"  Found {len(functions)} functions with register usage")
    
    reg_to_funcs = build_reg_to_funcs_map(reg_vars, functions)
    print(f"  Mapped {len(reg_to_funcs)} register addresses to functions")
    
    print(f"\nUpdating {COMMANDS_JSON}...")
    updated = update_commands_json(COMMANDS_JSON, reg_to_funcs)
    print(f"  Updated {updated} commands with script_functions")
    
    print("\nDone!")


if __name__ == '__main__':
    main()
