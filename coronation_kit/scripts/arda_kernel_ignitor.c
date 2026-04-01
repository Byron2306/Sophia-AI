#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/stat.h>
#include <linux/bpf.h>
#include <bpf/bpf.h>
#include <bpf/libbpf.h>

struct arda_identity {
    unsigned long long inode;
    unsigned int dev;
    unsigned int pad;
};

int main(int argc, char **argv) {
    if (argc < 5) {
        fprintf(stderr, "Usage: %s <prog_pin> <harmony_map_pin> <state_map_pin> <mode: audit|enforce> <binary1> ...\n", argv[0]);
        return 1;
    }

    const char *prog_pin = argv[1];
    const char *map_pin = argv[2];
    const char *state_map_pin = argv[3];
    const char *mode = argv[4];
    const char *link_pin = "/sys/fs/bpf/arda_link";

    int enforcement = 0;
    if (strcmp(mode, "enforce") == 0) {
        enforcement = 1;
    } else if (strcmp(mode, "audit") != 0) {
        fprintf(stderr, "[FAIL] Invalid mode '%s'. Use 'audit' or 'enforce'.\n", mode);
        return 1;
    }

    printf("═══ ARDA KERNEL IGNITOR (v2.1) ═══\n");
    printf("[INFO] Mode: %s\n", enforcement ? "ENFORCEMENT" : "AUDIT");

    // 0. Cleanup old link
    unlink(link_pin);

    // 1. Open Maps
    int map_fd = bpf_obj_get(map_pin);
    if (map_fd < 0) {
        fprintf(stderr, "[FAIL] Could not open harmony map pin %s: %s\n", map_pin, strerror(errno));
        return 1;
    }

    int state_map_fd = bpf_obj_get(state_map_pin);
    if (state_map_fd < 0) {
        fprintf(stderr, "[FAIL] Could not open state map pin %s: %s\n", state_map_pin, strerror(errno));
        close(map_fd);
        return 1;
    }

    // 2. Set Sovereignty State
    unsigned int state_key = 0;
    unsigned int state_val = enforcement;
    if (bpf_map_update_elem(state_map_fd, &state_key, &state_val, BPF_ANY) < 0) {
        fprintf(stderr, "[FAIL] Failed to set sovereignty state: %s\n", strerror(errno));
        close(map_fd);
        close(state_map_fd);
        return 1;
    }
    printf("[OK] Sovereignty state set to: %s\n", mode);

    // 3. Seed Map
    printf("[INFO] Seeding Harmonic Identity Map...\n");
    
    // 3a. Explicitly seed the ignitor itself
    struct stat st_self;
    if (stat(argv[0], &st_self) == 0) {
        struct arda_identity self_key = {
            .inode = (unsigned long long)st_self.st_ino,
            .dev = (unsigned int)st_self.st_dev,
            .pad = 0
        };
        unsigned int val = 1;
        if (bpf_map_update_elem(map_fd, &self_key, &val, BPF_ANY) < 0) {
            fprintf(stderr, "[FAIL] Failed to seed ignitor self: %s\n", strerror(errno));
        } else {
            printf("[OK] Seeded Self: %s (inode=%llu, dev=%u)\n", argv[0], self_key.inode, self_key.dev);
        }
    }

    // 3b. Seed binaries from argv
    for (int i = 5; i < argc; i++) {
        struct stat st;
        if (stat(argv[i], &st) < 0) {
            fprintf(stderr, "[WARN] Could not stat %s: %s\n", argv[i], strerror(errno));
            continue;
        }

        struct arda_identity key = {
            .inode = (unsigned long long)st.st_ino,
            .dev = (unsigned int)st.st_dev,
            .pad = 0
        };
        unsigned int val = 1;

        if (bpf_map_update_elem(map_fd, &key, &val, BPF_ANY) < 0) {
            fprintf(stderr, "[FAIL] Failed to seed %s: %s\n", argv[i], strerror(errno));
        } else {
            printf("[OK] Seeded: %s (inode=%llu, dev=%u)\n", argv[i], key.inode, key.dev);
        }
    }

    // 4. Open Program
    int prog_fd = bpf_obj_get(prog_pin);
    if (prog_fd < 0) {
        fprintf(stderr, "[FAIL] Could not open pinned program at %s: %s\n", prog_pin, strerror(errno));
        close(map_fd);
        close(state_map_fd);
        return 1;
    }

    // 5. Attach & Pin (Persistent Link)
    printf("[INFO] Sealing Lawful Execution Hook...\n");
    DECLARE_LIBBPF_OPTS(bpf_link_create_opts, opts);
    int link_fd = bpf_link_create(prog_fd, 0, BPF_LSM_MAC, &opts);
    if (link_fd < 0) {
        fprintf(stderr, "[FAIL] bpf_link_create failed: %s\n", strerror(errno));
        close(map_fd);
        close(state_map_fd);
        close(prog_fd);
        return 1;
    }

    if (bpf_obj_pin(link_fd, link_pin) < 0) {
        fprintf(stderr, "[FAIL] Could not pin link to %s: %s\n", link_pin, strerror(errno));
        close(map_fd);
        close(state_map_fd);
        close(prog_fd);
        close(link_fd);
        return 1;
    }

    close(map_fd);
    close(state_map_fd);
    close(prog_fd);
    close(link_fd);
    printf("[OK] Arda Sovereignty Engaged and Pinned.\n");
    return 0;
}
