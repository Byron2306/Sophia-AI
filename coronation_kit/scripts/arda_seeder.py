#!/usr/bin/env python3
import os
import struct
import subprocess
import sys

def get_identity(path):
    try:
        st = os.stat(path)
        return st.st_ino, st.st_dev
    except FileNotFoundError:
        print(f"Error: {path} not found")
        return None

def seed_map(map_id, path):
    identity = get_identity(path)
    if not identity:
        return
    
    inode, dev = identity
    # Key: struct arda_identity { __u64 inode; __u32 dev; __u32 pad; }
    # Using JSON for BTF-aware maps (much more reliable than raw hex)
    key_json = f'{{"inode":{inode},"dev":{int(dev)},"pad":0}}'
    val_json = '1'
    
    cmd = f"bpftool map update id {map_id} key '{key_json}' value {val_json}"
    print(f"[SEED] {path} (inode={inode}, dev={dev})")
    try:
        subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        print(f"[FAIL] {e.stderr.strip()}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: arda_seeder.py <map_id> <path1> <path2> ...")
        sys.exit(1)
    
    map_ref = sys.argv[1]
    paths = sys.argv[2:]
    
    for p in paths:
        seed_map(map_ref, p)
