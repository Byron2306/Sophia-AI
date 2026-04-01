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
    if (argc < 3) {
        fprintf(stderr, "Usage: %s <map_pin_path> <binary1> <binary2> ...\n", argv[0]);
        return 1;
    }

    const char *map_pin = argv[1];

    printf("═══ ARDA SEED TEST ER ═══\n");
    printf("[INFO] sizeof(struct arda_identity) = %zu\n", sizeof(struct arda_identity));

    int map_fd = bpf_obj_get(map_pin);
    if (map_fd < 0) {
        fprintf(stderr, "[FAIL] Could not open map pin %s: %s\n", map_pin, strerror(errno));
        return 1;
    }

    for (int i = 2; i < argc; i++) {
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
            fprintf(stderr, "[FAIL] Failed to seed %s: %s (errno=%d)\n", argv[i], strerror(errno), errno);
        } else {
            printf("[OK] Seeded: %s (inode=%llu, dev=%u)\n", argv[i], key.inode, key.dev);
        }
    }
    close(map_fd);
    return 0;
}
