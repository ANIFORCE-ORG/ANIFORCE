#!/usr/bin/env bash
# ============================================================
#  ANIFORCE 日志轮转脚本
#  用于处理前端和 Nginx 日志的按日期轮转
#  建议通过 cron 在每天午夜运行
# ============================================================
set -euo pipefail

# ---------- 颜色 ----------
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
fail()  { echo -e "${RED}[FAIL]${NC}  $*"; exit 1; }

# ---------- 默认参数 ----------
LOG_DIR="./logs"
COMPRESS=false
RETENTION_DAYS=30

# ---------- 参数解析 ----------
while [[ $# -gt 0 ]]; do
  case "$1" in
    --log-dir) LOG_DIR="$2"; shift 2 ;;
    --compress) COMPRESS=true; shift 1 ;;
    --retention) RETENTION_DAYS="$2"; shift 2 ;;
    -h|--help)
      echo "用法: $0 [选项]"
      echo ""
      echo "选项:"
      echo "  --log-dir DIR        日志目录 (默认: ./logs)"
      echo "  --compress           压缩旧日志文件"
      echo "  --retention DAYS     保留天数 (默认: 30)"
      echo ""
      echo "示例:"
      echo "  # 基本用法"
      echo "  $0"
      echo ""
      echo "  # 压缩旧日志并保留 7 天"
      echo "  $0 --compress --retention 7"
      echo ""
      echo "Cron 配置示例（每天午夜运行）:"
      echo "  0 0 * * * /path/to/rotate_logs.sh --log-dir /path/to/logs --compress"
      exit 0 ;;
    *) fail "未知参数: $1  (使用 --help 查看帮助)" ;;
  esac
done

# ---------- 项目根目录 ----------
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# 转换为绝对路径
if [[ "$LOG_DIR" != /* ]]; then
  LOG_DIR="$ROOT_DIR/$LOG_DIR"
fi

if [ ! -d "$LOG_DIR" ]; then
  warn "日志目录不存在: $LOG_DIR"
  exit 0
fi

info "========== 日志轮转开始 =========="
info "日志目录: $LOG_DIR"
info "保留天数: $RETENTION_DAYS"
info "压缩选项: $COMPRESS"

ROTATED=0
COMPRESSED=0
DELETED=0

# ---------- 1. 清理过期日志 ----------
info "清理 $RETENTION_DAYS 天前的日志..."

if [ "$COMPRESS" = true ]; then
  # 删除压缩的旧日志
  while IFS= read -r -d '' file; do
    rm -f "$file"
    DELETED=$((DELETED + 1))
    ok "已删除: $(basename "$file")"
  done < <(find "$LOG_DIR" -name "*.log.gz" -mtime +$RETENTION_DAYS -print0 2>/dev/null || true)
fi

# 删除未压缩的旧日志
while IFS= read -r -d '' file; do
  rm -f "$file"
  DELETED=$((DELETED + 1))
  ok "已删除: $(basename "$file")"
done < <(find "$LOG_DIR" -name "*.log" -mtime +$RETENTION_DAYS -print0 2>/dev/null || true)

# ---------- 2. 压缩旧日志 ----------
if [ "$COMPRESS" = true ]; then
  info "压缩 1 天前的日志..."
  
  # 压缩 1 天前的日志文件（排除今天的）
  while IFS= read -r -d '' file; do
    if [ ! -f "$file.gz" ]; then
      gzip "$file"
      COMPRESSED=$((COMPRESSED + 1))
      ok "已压缩: $(basename "$file")"
    fi
  done < <(find "$LOG_DIR" -name "*.log" -mtime +1 -print0 2>/dev/null || true)
fi

# ---------- 3. 统计信息 ----------
TOTAL_SIZE=$(du -sh "$LOG_DIR" 2>/dev/null | awk '{print $1}')
FILE_COUNT=$(find "$LOG_DIR" -type f | wc -l | tr -d ' ')

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  日志轮转完成${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo -e "  轮转文件数:    ${CYAN}$ROTATED${NC}"
echo -e "  压缩文件数:    ${CYAN}$COMPRESSED${NC}"
echo -e "  删除文件数:    ${CYAN}$DELETED${NC}"
echo -e "  当前文件数:    ${CYAN}$FILE_COUNT${NC}"
echo -e "  目录总大小:    ${CYAN}$TOTAL_SIZE${NC}"
echo ""

ok "日志轮转完成"
