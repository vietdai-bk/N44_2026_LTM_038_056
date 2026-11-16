#!/usr/bin/env bash
# Gắn kịch bản ns3/scratch/uav_lte vào cây NS-3 (symlink) rồi build.
# Dùng: ns3/install.sh [NS3_DIR]   (mặc định ~/simulation/ns-3.47)
set -euo pipefail
NS3_DIR="${1:-${NS3_DIR:-$HOME/simulation/ns-3.47}}"
SRC="$(cd "$(dirname "$0")" && pwd)/scratch/uav_lte"
[ -x "$NS3_DIR/ns3" ] || { echo "Không thấy NS-3 tại $NS3_DIR" >&2; exit 1; }
# symlink trỏ vào thư mục không còn tồn tại làm cmake lỗi khi configure
find "$NS3_DIR/scratch" -maxdepth 1 -xtype l -print -delete
ln -sfn "$SRC" "$NS3_DIR/scratch/uav_lte"
cd "$NS3_DIR" && ./ns3 build uav-lte
