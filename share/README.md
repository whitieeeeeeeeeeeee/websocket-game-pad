# WiFi-SPI Controller (WebSocket Game Pad)

基于 **Vue 3 + TypeScript** (前端) 和 **FastAPI + Python** (后端) 的游戏手柄 WebSocket 控制器，支持实时手柄输入、TCP 服务端、录制回放、网络调试等功能。

## 快速开始

### 前置要求

- **Python 3.8+** (推荐 3.10+)
- **Windows** 系统（手柄输入需要 `inputs` 库，Windows 原生支持）

### 一键启动

```bash
# 进入 share 目录
cd share

# 安装依赖并启动
python start.py
```

`start.py` 会自动：
1. 检查并安装 Python 依赖（fastapi, uvicorn, inputs 等）
2. 配置 Windows 防火墙规则
3. 启动后端服务
4. 打开浏览器访问 `http://localhost:8000`

### 手动启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务
python -m uvicorn api.main:app --host 0.0.0.0 --port 8000
```

然后浏览器访问 `http://localhost:8000`。

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

- `host`：服务监听地址
- `port`：服务监听端口
- `controller_send_mode`：发送模式（`continuous` 持续发送 / `onchange` 改变发送）

## 目录结构

```
share/
├── api/              # 后端 Python 代码
│   ├── main.py       # FastAPI 主应用
│   ├── controller.py # 手柄管理
│   ├── tcp_server.py # TCP 服务端
│   ├── recorder.py   # 录制回放
│   ├── network_service.py  # 网络服务
│   └── mock_service.py     # Mock 设备
├── dist/             # 编译好的前端（静态文件）
├── public/           # 静态资源（favicon）
├── config.json       # 配置文件
├── requirements.txt  # Python 依赖
├── start.py          # 启动脚本
└── start.bat         # Windows 启动脚本
```

## 开发

如需从源码构建前端：

```bash
# 安装 Node.js 依赖
npm install

# 开发模式
npm run dev

# 构建生产版本
npm run build
```

## License

MIT License - 详见 [LICENSE](LICENSE)

---

Powered By whitiee
