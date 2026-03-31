#!/usr/bin/env bash
# resources.sh — One-shot system resource snapshot as JSON.
#
# Usage: scripts/monitor/resources.sh
# Output: JSON to stdout with cpu, mem, disk_free_gb
set -euo pipefail

# CPU: sum of all process CPU / number of cores
CORES=$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)
CPU=$(ps -A -o %cpu | awk -v cores="$CORES" 'NR>1{sum+=$1} END{printf "%.1f", sum/cores}')

# Memory: macOS vm_stat or Linux /proc/meminfo
if command -v vm_stat &>/dev/null; then
  PAGE_SIZE=$(vm_stat | head -1 | grep -o '[0-9]*')
  FREE=$(vm_stat | awk '/Pages free/{gsub(/\./,"",$3); print $3}')
  INACTIVE=$(vm_stat | awk '/Pages inactive/{gsub(/\./,"",$3); print $3}')
  TOTAL_PAGES=$(sysctl -n hw.memsize 2>/dev/null)
  TOTAL_GB=$(echo "$TOTAL_PAGES" | awk '{printf "%.1f", $1/1073741824}')
  FREE_BYTES=$(( (FREE + INACTIVE) * PAGE_SIZE ))
  USED_PCT=$(echo "$TOTAL_PAGES $FREE_BYTES" | awk '{printf "%.1f", ($1-$2)/$1*100}')
else
  TOTAL_GB=$(awk '/MemTotal/{printf "%.1f", $2/1048576}' /proc/meminfo 2>/dev/null || echo "0")
  AVAIL=$(awk '/MemAvailable/{print $2}' /proc/meminfo 2>/dev/null || echo "0")
  TOTAL_KB=$(awk '/MemTotal/{print $2}' /proc/meminfo 2>/dev/null || echo "1")
  USED_PCT=$(echo "$TOTAL_KB $AVAIL" | awk '{printf "%.1f", ($1-$2)/$1*100}')
fi

# Disk
DISK_FREE_GB=$(df -g / 2>/dev/null | awk 'NR==2{print $4}' || df -BG / 2>/dev/null | awk 'NR==2{gsub(/G/,"",$4); print $4}' || echo "0")

printf '{"cpu":%s,"mem":%s,"disk_free_gb":%s}\n' "$CPU" "$USED_PCT" "$DISK_FREE_GB"
