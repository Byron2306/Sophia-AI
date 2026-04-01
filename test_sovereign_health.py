#!/usr/bin/env python3
import os
import sys
import json
import hashlib
import asyncio
import logging
import shutil

# Set up logging for Arda Sovereign Audit
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ARDA_SOVEREIGN_AUDIT")

# Claim 5 Solution: Flexible pathing for manifest location
MANIFEST_PATH = "arda_os/sovereign_manifest.json" if os.path.exists("arda_os/sovereign_manifest.json") else "sovereign_manifest.json"
MOCK_STORAGE = "/tmp/arda_secure_storage"
TARGET_BINARY = "/usr/bin/bash"

def get_physical_hash(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

def get_manifest_hash(path, binary_key):
    try:
        with open(path, "r") as f:
            manifest = json.load(f)
        return manifest.get(binary_key, "").replace("sha256:", "")
    except FileNotFoundError:
        logger.error(f"[AUDIT] Manifest not found at {path}")
        return None

async def run_definitive_audit():
    logger.info("--- STARTING DEFINITIVE SOVEREIGN HEALTH AUDIT (CLAIM 5 & 10) ---")
    logger.info(f"[AUDIT] Using manifest at: {MANIFEST_PATH}")
    
    # 0. Initial State (Harmony)
    physical_truth = get_physical_hash(TARGET_BINARY)
    manifest_claim = get_manifest_hash(MANIFEST_PATH, TARGET_BINARY)
    
    if manifest_claim is None:
        logger.critical("AUDIT ABORTED: Missing security substrate.")
        return

    logger.info(f"GATE 0: Initial State Check")
    logger.info(f"  Physical Truth: {physical_truth[:16]}...")
    logger.info(f"  Manifest Claim: {manifest_claim[:16]}...")
    
    if physical_truth == manifest_claim:
        logger.info("  STATUS: HARMONIOUS (LAWFUL)")
    else:
        logger.warning("  STATUS: DISSONANT (Initial state was not clean)")

    # 1. Inject Dissonance
    logger.info("\nGATE 1: Injecting Dissonance (Corruption)")
    with open(MANIFEST_PATH, "r") as f:
        manifest = json.load(f)
    manifest[TARGET_BINARY] = "sha256:DEADBEEF_MANIFEST_FRACTURE"
    with open(MANIFEST_PATH, "w") as f:
        json.dump(manifest, f, indent=2)
    
    new_claim = get_manifest_hash(MANIFEST_PATH, TARGET_BINARY)
    logger.info(f"  New Manifest Claim: {new_claim}")
    logger.info("  STATUS: UNLAWFUL (Dissonance Injected)")

    # 2. Machinic Restoration (The "Self-Healing" Proof)
    logger.info("\nGATE 2: Engaging Machinic Restoration (Autonomous Healing)")
    
    # Prepare secure storage (The "Known Good" source)
    os.makedirs(MOCK_STORAGE, exist_ok=True)
    # Binary name mapped from manifest key to secure storage filename
    shutil.copy(TARGET_BINARY, os.path.join(MOCK_STORAGE, "bash.sh"))
    
    from arda_os.backend.services.restoration_controller import RestorationController
    controller = RestorationController(MANIFEST_PATH, MOCK_STORAGE)
    
    # SYSTEM CALLS ITS OWN RECOVERY
    logger.info("  [SYSTEM ACTION] Restoration pleaded for /usr/bin/bash...")
    success = await controller.plea_for_restoration(TARGET_BINARY, "Autonomous_Kernel_Self_Test")
    
    if success:
        logger.info("  [SYSTEM ACTION] Restoration VERDICT: GRANT. Manifest mended.")
    else:
        logger.error("  [SYSTEM ACTION] Restoration VERDICT: DENY. Healing failed.")

    # 3. Final Audit (The "Lawful State" Proof)
    logger.info("\nGATE 3: Final Sovereign Audit")
    final_claim = get_manifest_hash(MANIFEST_PATH, TARGET_BINARY)
    
    logger.info(f"  Physical Truth: {physical_truth[:16]}...")
    logger.info(f"  Manifest Claim: {final_claim[:16]}...")
    
    if physical_truth == final_claim:
        logger.info("  STATUS: HARMONY RESTORED (LAWFUL SUCCESS)")
    else:
        logger.error("  STATUS: DISSONANCE PERSISTS. The Healing failed.")

    logger.info("\n--- DEFINITIVE AUDIT COMPLETE ---")

if __name__ == "__main__":
    sys.path.append(os.getcwd())
    asyncio.run(run_definitive_audit())
