# WiFi-SPI Controller (WebSocket Game Pad)

基于 **Vue 3 + TypeScript** (前端) 和 **FastAPI + Python** (后端) 的游戏手柄 WebSocket 控制器，支持实时手柄输入、TCP 服务端、录制回放、网络调试等功能。

## 快速开始

### 前置要求

- **Python 3.8+** (推荐 3.10+)
- **Node.js 16+** (仅开发需要)
- **Windows** 系统（手柄输入需要 `inputs` 库，Windows 原生支持）

### 使用编译好的 Release（推荐）

1. 下载 `share/` 目录
2. 运行 `python start.py`
3. 浏览器自动打开 `http://localhost:8000`

### 从源码构建

```bash
# 克隆仓库
git clone https://github.com/whitieeeeeeeeeeeee/websocket-game-pad.git
cd websocket-game-pad

# 安装前端依赖并构建
npm install
npm run build

# 安装后端依赖
pip install -r requirements.txt

# 启动服务
python start.py
```

## 功能特性

- **手柄输入**：支持 Xbox/PS 手柄，实时检测按键、摇杆、扳机状态
- **TCP 服务端**：内置 TCP 服务器，支持多客户端连接，客户端列表管理
- **WebSocket 通信**：浏览器实时显示手柄状态，JSON 格式数据传输
- **录制回放**：支持录制手柄操作并回放，可调倍速（0.5x/1x/2x/自定义）
- **发送模式**：持续发送（按频率）或改变发送（状态变化时发送）
- **网络调试**：支持 HEX/文本格式收发，UTF-8/GBK 编码
- **Mock 设备**：内置模拟手柄用于无手柄环境测试

## 数据协议

手柄状态以 JSON 格式发送：

```json
{
  "btns": {
    "A": false, "B": false, "X": false, "Y": false,
    "LB": false, "RB": false,
    "Back": false, "Start": false,
    "LS": false, "RS": false,
    "DpadUp": false, "DpadDown": false,
    "DpadLeft": false, "DpadRight": false
  },
  "axes": {
    "LX": 0.0, "LY": 0.0,
    "RX": 0.0, "RY": 0.0
  },
  "trigs": {
    "LT": 0.0, "RT": 0.0
  }
}
```

- `btns`：按键状态（`true` 按下，`false` 释放）
- `axes`：摇杆轴值（范围 `-1.0` ~ `1.0`）
- `trigs`：扳机值（范围 `0.0` ~ `1.0`）

## 配置

编辑 `config.json`：

```json
{
  "host": "0.0.0.0",
  "port": 8000,
  "controller_send_mode": "onchange"
}
```

## 目录结构

```
.
├── api/              # 后端 Python 代码
├── src/              # 前端 Vue 3 源码
├── share/            # 编译好的轻量 Release（可直接运行）
│   ├── api/          # 后端代码
│   ├── dist/         # 编译好的前端静态文件
│   ├── public/       # 静态资源
│   ├── config.json   # 默认配置
│   ├── requirements.txt
│   └── start.py      # 启动脚本
├── package.json      # 前端依赖配置
├── requirements.txt  # 后端依赖
└── start.py          # 启动脚本
```

## 开发

```bash
# 前端开发模式（热重载）
npm run dev

# 类型检查
npm run check

# 代码规范检查
npm run lint

# 构建生产版本
npm run build
```

## License

MIT License

---

Powered By whitiee
