#!/usr/bin/env python3
import os
import subprocess
import json
import sys

def restore():
    print("ARDA OS: RESURRECTING SOVEREIGN STATE (v2.3)...")
    
    if os.getuid() != 0:
        print("ERROR: Resurrection requires root privileges.")
        sys.exit(1)

    print("[1] Discovering Physical Identities...")
    try:
        result = subprocess.check_output(['python3', 'arda_os/backend/services/arda_seeder.py', '--tier', 'critical'], text=True)
        binaries = json.loads(result)
        print(f"Found {len(binaries)} critical identities.")
    except Exception as e:
        print(f"ERROR during discovery: {e}")
        sys.exit(1)

    print("[2] Seeding Harmony Map...")
    try:
        with open("/tmp/arda_identities.json", "w") as f:
            json.dump(binaries, f)
        subprocess.check_call(['python3', 'arda_os/arda_map_seeder_final.py', '--json-file', '/tmp/arda_identities.json'])
        os.remove("/tmp/arda_identities.json")
    except Exception as e:
        print(f"ERROR during seeding: {e}")
        sys.exit(1)

    print("[3] Engaging Ring-0 Enforcement...")
    try:
        output = subprocess.check_output(['sudo', 'bpftool', 'map', 'show', '-j'], text=True)
        maps = json.loads(output)
        state_map_id = next((m['id'] for m in maps if m.get('name', '').startswith('arda_state')), None)
        
        if state_map_id:
            subprocess.check_call(['sudo', 'bpftool', 'map', 'update', 'id', str(state_map_id), 'key', '0', '0', '0', '0', 'value', '1', '0', '0', '0'])
            print("SUCCESS: Enforcement active.")
        else:
            print("WARNING: arda_state map not found.")
    except Exception as e:
        print(f"ERROR during enforcement: {e}")

    print("ARDA OS: RESURRECTION COMPLETE.")

if __name__ == "__main__":
    restore()
