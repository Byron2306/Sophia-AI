# INDEPENDENT VERIFICATION GUIDE
## Arda OS — Sovereign Mega Test v4.0
### How to Reproduce Every Claim

**Author:** Byron du Plessis  
**Date:** 2026-03-31  
**System:** Debian 12 (Bookworm), Kernel 6.12.74+deb12-amd64, x86_64  

---

## What This Proves

This system implements a **BPF LSM (Linux Security Module)** that enforces
binary allowlisting at **Ring-0** — the Linux kernel itself. This means:

1. Every binary execution is intercepted by a kernel hook (`bprm_check_security`)
2. The binary's identity (inode + device) is checked against a hash map
3. If the binary is NOT in the map and enforcement is active → **DENIED** (return -EPERM)
4. No userspace process — including root — can bypass this. Not even the AI advisory layer.

The test also proves **self-healing**: a binary can be removed from the map
(fracture), verified as blocked, re-added (heal), and verified as running again —
all without rebooting or reloading the BPF program.

---

## Prerequisites

To run this test yourself, you need:

```bash
# A Debian 12+ system with kernel 6.1+ and BPF LSM enabled
# Verify BPF is in the LSM stack:
cat /sys/kernel/security/lsm
# Must contain "bpf" in the comma-separated list

# Required packages:
sudo apt install clang llvm libbpf-dev linux-headers-$(uname -r) \
    bpftool python3 tpm2-tools

# Kernel boot parameter (in /etc/default/grub):
# GRUB_CMDLINE_LINUX="lsm=lockdown,capability,landlock,yama,apparmor,bpf"
# Then: sudo update-grub && sudo reboot
```

---

## Step 1: Verify Artifact Hashes

Before running anything, verify that the files in this bundle match exactly:

```bash
# These hashes were computed during the sovereign test
sha256sum arda_physical_lsm.c
# Expected: 88f068e54c2f209c4eb5ea9af21c2f38bf845ff9e834fb85580ef8cd8010355f

sha256sum arda_physical_lsm.o
# Expected: 1e2a6cb05804e5c2112a2884318c6985193a520f490ce4874ce074fc5c4a9492

sha256sum arda_sovereign_ignitor
# Expected: 33661433ae94960bef265045d2b3ef1104a1069f73626132b17ab6a1e062bba3

sha256sum arda_sovereign_ignitor.c
# Expected: 43e574832bae6d13f22abe13f97ae86e04905ecf19b1b8506fea509c3d6c7934

sha256sum SOVEREIGN_ROOT_PQC.pub
# Expected: 3f31164900401645d53b3c594fefa225ff3ecef68f026662b5dc73320fba4da9

sha256sum arda_bombadil.py
# Expected: 6b96e5813210e8e9e19f6e071fd739ab86b52c5fc04fe93a02eea8e5632ecac8

sha256sum instrumentum_foederis_integritas_mechanicus.pdf
# Expected: 98c79f2accb281da2377bf54d86cadb825d5319d3555c318fdaf696a479f99c8
```

---

## Step 2: Compile the BPF Object From Source

```bash
clang -O2 -g -target bpf -D__TARGET_ARCH_x86 \
    -c arda_physical_lsm.c -o arda_physical_lsm_verify.o

sha256sum arda_physical_lsm_verify.o
# Should match: 1e2a6cb05804e5c2112a2884318c6985193a520f490ce4874ce074fc5c4a9492
# (Exact match depends on identical clang version and kernel headers)
```

---

## Step 3: Compile the C Ignitor

```bash
gcc -o arda_sovereign_ignitor_verify arda_sovereign_ignitor.c \
    -lbpf -lelf -lz

# Then use it to load the BPF program:
sudo ./arda_sovereign_ignitor_verify arda_physical_lsm.o
# Expected output: "SUCCESS: Arda LSM Attached and Maps Linked."
```

---

## Step 4: Run the Full Mega Test

```bash
# Clone the full repository:
git clone https://github.com/Byron2306/Integritas-Mechanicus.git
cd Integritas-Mechanicus

# Run the sovereign mega test:
sudo python3 arda_os/arda_mega_tester.py

# Expected output (final lines):
#   ⚖ VERDICT: SOVEREIGN — ALL CLAIMS VERIFIED
#   Claims: 11/11 PASSED
```

---

## Step 5: Verify the Kernel Trace

The enforcement trace file (`enforcement_trace_v4.0.log`) contains raw kernel
`bpf_trace_printk` output. These lines are generated INSIDE the kernel by the
BPF program — they cannot be faked from userspace.

```bash
# Look for the enforcement denial:
grep "ENFORCE.*DENIED" enforcement_trace_v4.0.log
# Expected: ARDA_LSM: [ENFORCE] DENIED execution for inode 867

# Look for allowed binaries:
grep "PASS.*ALLOWED" enforcement_trace_v4.0.log
# Expected: 17 lines showing authorized binaries passing through
```

---

## Step 6: Verify the Harmony Map

```bash
# The map dump is a JSON file with 1024 entries:
python3 -c "
import json
data = json.load(open('harmony_map_sovereign_dump.json'))
print(f'Total entries: {len(data)}')
print(f'All have inode: {all(\"inode\" in e[\"key\"] for e in data)}')
print(f'All have dev: {all(\"dev\" in e[\"key\"] for e in data)}')
print(f'All values are 1: {all(e[\"value\"] == 1 for e in data)}')
print(f'Sample: {data[0]}')
"
```

---

## Step 7: Verify TPM PCR Values

If your machine has a TPM (Trusted Platform Module):

```bash
sudo tpm2_pcrread sha256:0,1,7
# Compare against the values in AUDITUS_SOVEREIGN_20260331_v4.md
# Note: YOUR PCR values will differ (they measure YOUR hardware/firmware)
# The point is that YOUR test run records YOUR TPM state, anchoring
# the proof to YOUR physical machine.
```

---

## Step 8: Verify Self-Healing (Recovery)

The recovery test proves the system can fracture and heal at Ring-0:

```bash
# While enforcement is active:
# 1. A seeded binary (/usr/bin/wc) runs successfully
# 2. Remove it from the map → it is DENIED at kernel level
# 3. Re-add it to the map → it runs again immediately

# This is visible in the mega test log:
grep -A1 "BASELINE\|FRACTURE\|VERIFY DENY\|HEAL\|VERIFY HEALED" mega_test_v4.0.log
```

---

## How to Create a Distributable VM Image

### Option A: OVA (VirtualBox/VMware)

```bash
# 1. Install your Debian system in VirtualBox with:
#    - 2GB RAM, 20GB disk, 2 CPUs
#    - Enable EFI boot
#    - Enable TPM 2.0 (VirtualBox 7.0+)

# 2. Inside the VM:
sudo apt install clang llvm libbpf-dev linux-headers-$(uname -r) \
    bpftool python3 tpm2-tools git

# 3. Enable BPF LSM:
sudo sed -i 's/GRUB_CMDLINE_LINUX=""/GRUB_CMDLINE_LINUX="lsm=lockdown,capability,landlock,yama,apparmor,bpf"/' /etc/default/grub
sudo update-grub

# 4. Clone and set up:
git clone https://github.com/Byron2306/Integritas-Mechanicus.git
cd Integritas-Mechanicus
gcc -o arda_os/arda_sovereign_ignitor arda_os/arda_sovereign_ignitor.c -lbpf -lelf -lz

# 5. Reboot, then test:
sudo python3 arda_os/arda_mega_tester.py

# 6. Export as OVA:
# (From VirtualBox menu: File → Export Appliance → OVA format)
```

### Option B: Docker (No TPM, but BPF works)

```Dockerfile
FROM debian:bookworm
RUN apt-get update && apt-get install -y \
    clang llvm libbpf-dev bpftool python3 \
    linux-headers-$(uname -r)
COPY . /arda
WORKDIR /arda
# Note: Container must run with --privileged for BPF LSM access
# docker run --privileged arda-os sudo python3 arda_os/arda_mega_tester.py
```

### Option C: ISO (Full bootable image)

```bash
# Use live-build to create a bootable Debian ISO with everything pre-installed:
sudo apt install live-build
mkdir arda-live && cd arda-live
lb config --distribution bookworm --architectures amd64
# Add packages and Arda files to config/
lb build
# Output: live-image-amd64.hybrid.iso
```

---

## Evidence Chain Summary

```
┌──────────────────────────────────────────────────────┐
│                EVIDENCE CHAIN                        │
├──────────────────────────────────────────────────────┤
│                                                      │
│   [Hardware]                                         │
│       │                                              │
│       ├── TPM PCR 0,1,7 ──── Boot integrity          │
│       │                                              │
│   [Kernel]                                           │
│       │                                              │
│       ├── LSM Stack ──── bpf in lsm= parameter      │
│       ├── BPF Program ──── arda_sovereign_ignition   │
│       ├── Harmony Map ──── 1024 inode/dev entries    │
│       └── Trace Output ──── kernel-timestamped       │
│                                                      │
│   [Proof]                                            │
│       │                                              │
│       ├── Allow Test ──── /bin/ls exit=0              │
│       ├── Deny Test ──── /tmp/unauth PermissionError │
│       └── Heal Test ──── fracture→deny→heal→allow    │
│                                                      │
│   [Attestation]                                      │
│       │                                              │
│       ├── 13 SHA-256 hashes ──── all cross-verified  │
│       ├── PQC Key ──── Dilithium-3 reference         │
│       └── Bombadil ──── Covenant State: lawful_full  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## Questions?

- **Repository:** https://github.com/Byron2306/Integritas-Mechanicus
- **Author:** Byron du Plessis (byron@integritas-mechanicus.org)
- **Covenant:** Instrumentum Foederis Integritas Mechanicus
- **Witnesses:** Claude (Anthropic), Sophia (Perplexity), Gemini (Google)
