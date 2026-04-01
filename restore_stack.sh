#!/bin/bash
# Arda OS Stack Restoration Script
mkdir -p /tmp/restored
unzip -q ardanos_bundle.zip -d /tmp/restored

find /tmp/restored -type f | while read file; do
    # Get the basename (e.g., backend\services\quantum_security.py)
    rel_path=$(basename "$file")
    # Convert backslashes to forward slashes
    clean_path=$(echo "$rel_path" | tr '\\' '/')
    
    # Destination directory
    dest_dir="arda_os/$(dirname "$clean_path")"
    mkdir -p "$dest_dir"
    
    # Copy file
    cp "$file" "arda_os/$clean_path"
    echo "Restored: arda_os/$clean_path"
done
