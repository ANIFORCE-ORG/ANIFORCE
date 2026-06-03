# 跨平台兼容性说明

## 问题背景

原始脚本使用 `lsof` 命令进行端口检查和进程管理，但 `lsof` 在不同操作系统和 Linux 发行版上存在兼容性问题：

### lsof 的局限性

1. **某些 Linux 发行版未预装**
   - Alpine Linux（Docker 常用基础镜像）
   - 最小化安装的 CentOS/Ubuntu
   - 某些嵌入式 Linux 系统

2. **权限要求**
   - 某些系统需要 root 权限
   - 云服务器可能有安全限制

3. **命令参数差异**
   - 不同版本的 lsof 行为可能不同
   - macOS 和 Linux 的 lsof 实现略有差异

## 解决方案

### 跨平台端口检查函数

实现了多层回退机制，按优先级尝试不同的工具：

```bash
check_port_in_use() {
  local port=$1
  
  # 方法1: lsof（macOS 和部分 Linux）
  if command -v lsof &>/dev/null; then
    lsof -i :$port -sTCP:LISTEN &>/dev/null && return 0
  fi
  
  # 方法2: ss（现代 Linux）
  if command -v ss &>/dev/null; then
    ss -ltn | grep -q ":$port " && return 0
  fi
  
  # 方法3: netstat（传统 Linux/Unix）
  if command -v netstat &>/dev/null; then
    netstat -ltn 2>/dev/null | grep -q ":$port " && return 0
  fi
  
  # 方法4: nc（最后的手段）
  if command -v nc &>/dev/null; then
    nc -z localhost $port &>/dev/null && return 0
  fi
  
  # 假设端口未占用
  return 1
}
```

### 跨平台进程终止函数

```bash
kill_port_process() {
  local port=$1
  
  # 方法1: lsof（macOS 和部分 Linux）
  if command -v lsof &>/dev/null; then
    local pids=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      return 0
    fi
  fi
  
  # 方法2: fuser（Linux）
  if command -v fuser &>/dev/null; then
    fuser -k $port/tcp 2>/dev/null || true
    return 0
  fi
  
  # 方法3: ss（现代 Linux）
  if command -v ss &>/dev/null; then
    local pids=$(ss -lptn 2>/dev/null | grep ":$port " | awk '{print $6}' | grep -oP 'pid=\K[0-9]+' | sort -u)
    if [ -n "$pids" ]; then
      echo "$pids" | xargs kill -9 2>/dev/null || true
      return 0
    fi
  fi
  
  warn "无法自动清理端口 $port，请手动检查"
  return 1
}
```

## 工具优先级

### 端口检查优先级

| 优先级 | 工具 | 适用系统 | 优点 | 缺点 |
|-------|------|---------|------|------|
| 1 | `lsof` | macOS, 部分 Linux | 功能强大，信息详细 | 部分系统未预装 |
| 2 | `ss` | 现代 Linux | 速度快，现代工具 | 旧系统可能没有 |
| 3 | `netstat` | 所有 Unix/Linux | 兼容性最好 | 已被标记为过时 |
| 4 | `nc` | 大部分系统 | 简单直接 | 功能有限 |

### 进程终止优先级

| 优先级 | 工具 | 适用系统 | 优点 | 缺点 |
|-------|------|---------|------|------|
| 1 | `lsof` | macOS, 部分 Linux | 准确获取 PID | 部分系统未预装 |
| 2 | `fuser` | Linux | 专门用于端口管理 | macOS 不可用 |
| 3 | `ss` | 现代 Linux | 现代工具 | 需要解析输出 |

## 系统兼容性矩阵

### macOS

| 工具 | 可用性 | 说明 |
|------|--------|------|
| `lsof` | ✅ 预装 | 推荐使用 |
| `ss` | ❌ 不可用 | - |
| `netstat` | ✅ 预装 | 已过时但可用 |
| `nc` | ✅ 预装 | 备用方案 |
| `fuser` | ❌ 不可用 | - |

### Ubuntu/Debian

| 工具 | 可用性 | 说明 |
|------|--------|------|
| `lsof` | ⚠️ 需安装 | `apt install lsof` |
| `ss` | ✅ 预装 | 推荐使用 |
| `netstat` | ⚠️ 需安装 | `apt install net-tools` |
| `nc` | ✅ 预装 | 备用方案 |
| `fuser` | ✅ 预装 | psmisc 包 |

### CentOS/RHEL

| 工具 | 可用性 | 说明 |
|------|--------|------|
| `lsof` | ⚠️ 需安装 | `yum install lsof` |
| `ss` | ✅ 预装 | 推荐使用 |
| `netstat` | ⚠️ 需安装 | `yum install net-tools` |
| `nc` | ⚠️ 需安装 | `yum install nmap-ncat` |
| `fuser` | ✅ 预装 | psmisc 包 |

### Alpine Linux (Docker)

| 工具 | 可用性 | 说明 |
|------|--------|------|
| `lsof` | ⚠️ 需安装 | `apk add lsof` |
| `ss` | ✅ 预装 | 推荐使用 |
| `netstat` | ⚠️ 需安装 | `apk add net-tools` |
| `nc` | ⚠️ 需安装 | `apk add netcat-openbsd` |
| `fuser` | ⚠️ 需安装 | `apk add psmisc` |

## 使用示例

### 检查端口是否被占用

```bash
# 使用跨平台函数
if check_port_in_use 8010; then
  echo "端口 8010 已被占用"
else
  echo "端口 8010 可用"
fi

# 原始方法（仅 macOS/部分 Linux）
if lsof -i :8010 -sTCP:LISTEN &>/dev/null; then
  echo "端口 8010 已被占用"
fi
```

### 终止占用端口的进程

```bash
# 使用跨平台函数
kill_port_process 8010

# 原始方法（仅 macOS/部分 Linux）
lsof -ti :8010 | xargs kill -9 2>/dev/null || true
```

## 测试验证

### 在不同系统上测试

```bash
# macOS
./deploy_server.sh --mode local

# Ubuntu/Debian
./deploy_server.sh --mode cloud

# CentOS/RHEL
./deploy_server.sh --mode cloud

# Alpine Linux (Docker)
docker run -it alpine:latest sh
apk add bash
./deploy_server.sh
```

### 模拟工具缺失

```bash
# 临时禁用 lsof（测试回退机制）
alias lsof='echo "lsof not found" && false'
./deploy_server.sh

# 恢复
unalias lsof
```

## 故障排查

### 问题 1: 所有工具都不可用

**症状**: 脚本无法检查端口状态

**解决方案**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install lsof net-tools

# CentOS/RHEL
sudo yum install lsof net-tools

# Alpine
apk add lsof net-tools
```

### 问题 2: 权限不足

**症状**: `Permission denied` 错误

**解决方案**:
```bash
# 使用 sudo 运行脚本
sudo ./deploy_server.sh

# 或者给当前用户添加权限
sudo usermod -aG sudo $USER
```

### 问题 3: ss 命令输出格式不同

**症状**: ss 命令可用但端口检查失败

**解决方案**:
```bash
# 检查 ss 输出格式
ss -ltn

# 调整 grep 模式（如需要）
ss -ltn | grep ":8010"
```

## 最佳实践

### 1. 优先使用系统自带工具

```bash
# 好的做法：检查工具是否存在
if command -v lsof &>/dev/null; then
  # 使用 lsof
fi

# 不好的做法：直接使用
lsof -i :8010  # 可能失败
```

### 2. 提供多层回退

```bash
# 好的做法：多个备选方案
check_port_in_use() {
  # 尝试方法1
  # 尝试方法2
  # 尝试方法3
}

# 不好的做法：单一方法
lsof -i :$port  # 系统不支持就失败
```

### 3. 优雅降级

```bash
# 好的做法：无法清理时给出提示
if ! kill_port_process $port; then
  warn "无法自动清理端口，请手动检查"
fi

# 不好的做法：直接失败
kill_port_process $port || exit 1
```

## 已更新的文件

1. **deploy_server.sh**
   - 添加 `check_port_in_use()` 函数
   - 添加 `kill_port_process()` 函数
   - 替换所有 `lsof` 调用

2. **run_server.sh**
   - 添加 `check_port_in_use()` 函数
   - 添加 `kill_port_process()` 函数
   - 替换所有 `lsof` 调用

## 验证清单

- [x] macOS 兼容性
- [x] Ubuntu/Debian 兼容性
- [x] CentOS/RHEL 兼容性
- [x] Alpine Linux 兼容性
- [x] 工具缺失时的回退机制
- [x] 权限不足时的错误处理
- [x] 详细的错误提示

## 相关文档

- `DEPLOYMENT.md` - 部署文档
- `README.md` - 项目说明
- `deploy_server.sh` - 部署脚本
- `run_server.sh` - 运行脚本
