import os
import sys

# Set up PYTHONPATH
arda_home = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(arda_home, "arda_os"))
sys.path.append(os.path.join(arda_home, "arda_os", "backend"))

from arda_os.backend.services.os_enforcement_service import OsEnforcementService

# Mocking env
os.environ["ARDA_SOVEREIGN_MODE"] = "1"

print("Initializing OsEnforcementService...")
try:
    # Use the compiled object we just made
    svc = OsEnforcementService(bpf_source="arda_os/backend/services/bpf/arda_physical_lsm.c")
    print("Service initialized.")
    if svc.is_authoritative:
        print("Service is AUTHORITATIVE (LSM ready).")
    else:
        print("Service is in MOCK mode (expected if BCC is missing).")
    
    # Test manifest verification logic
    test_path = "/usr/bin/bash"
    test_hash = "223fe8564b60636bc738b6178d3ba9a50ef7d791266b0efae6363bb716e4c47f"
    valid = svc._verify_manifest_integrity(test_path, test_hash)
    print(f"Manifest check for {test_path}: {'SUCCESS' if valid else 'FAILED'}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
