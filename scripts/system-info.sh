#!/bin/sh
set -u
echo "macOS: $(sw_vers -productVersion) ($(sw_vers -buildVersion))"
echo "Architecture: $(uname -m)"
echo "Chip: $(sysctl -n machdep.cpu.brand_string 2>/dev/null || echo unknown)"
bytes=$(sysctl -n hw.memsize 2>/dev/null || echo 0)
echo "Unified memory: $((bytes / 1073741824)) GiB"
echo "Python: $(python3 --version 2>&1)"
echo "uv: $(uv --version 2>&1 || echo unavailable)"
echo "Xcode tools: $(xcode-select -p 2>&1 || echo unavailable)"
echo "MLX packages:"
uv pip list 2>/dev/null | awk 'BEGIN{IGNORECASE=1} /^mlx([ -]|$)/ {print "  "$0}'
