# WiFi-SPI 控制器 Web 界面设计要求文档

> 本文档面向专业设计 AI，用于指导 WiFi-SPI 控制器 Web 界面的视觉设计与交互设计实现。

---

## 一、项目概述

**WiFi-SPI 控制器** 是一个基于 Web 的手柄控制器配置和调试工具，通过 WebSocket 实时显示手柄状态，支持网络通信（UDP/TCP 客户端 + 服务端）、录制回放、按键映射配置。

### 核心能力

- **手柄状态实时展示**：通过 WebSocket 推送，实时显示手柄按键、摇杆、扳机状态。
- **网络通信**：支持 UDP/TCP 协议，可作客户端连接远端，也可作服务端接收多客户端连接。
- **录制回放**：录制手柄操作序列，支持回放（含速度控制、进度跳转、禁止真手柄模式）。
- **按键映射配置**：14 个按键可自定义发送内容与格式（文本/十六进制），支持导入导出。
- **实时日志**：通信日志与系统日志双通道，支持方向过滤、原始 JSON 切换、自动滚动。

### 技术约束

- 前端框架：Vue 3 + Element Plus（参考组件库风格，但不限制视觉再设计）
- 实时通信：WebSocket（`ws://localhost:8000/ws`）
- HTTP 基础地址：`http://localhost:8000`
- 目标浏览器：现代桌面浏览器（Chrome / Edge / Firefox 最新版）

---

## 二、页面结构

本项目共两个页面，通过路由切换。

### 页面 1：Dashboard（主控制面板）

- **路由**：`/`（根路径）
- **布局**：三栏布局（左 340px / 中自适应 / 右 380px），顶部状态栏
- **滚动行为**：页面整体不滚动，各面板内部独立滚动

#### 2.1.1 顶部状态栏（TopStatusBar）

水平通栏，固定高度。

| 位置 | 元素 | 说明 |
|------|------|------|
| 左侧 | 标题 | "WiFi-SPI 控制器" |
| 右侧 | 手柄配置链接 | 跳转至 `/config` |
| 右侧 | WebSocket 连接状态指示器 | 颜色指示：已连接（绿）/ 连接中（黄）/ 已断开（红） |
| 右侧 | 关闭服务按钮 | 调用 `POST /api/shutdown` |

#### 2.1.2 左栏 - 手柄状态面板（ControllerPanel）

栏宽 340px。

**（1）手柄可视化区域**

图形化展示游戏手柄，包含以下可交互/可高亮元素：

| 部件 | 数据来源 | 交互/高亮规则 |
|------|----------|---------------|
| 左摇杆 | LX/LY 轴 | 摇杆点位随轴值移动；LS 按钮按下时高亮 |
| 右摇杆 | RX/RY 轴 | 摇杆点位随轴值移动；RS 按钮按下时高亮 |
| 方向键 | DpadUp/DpadDown/DpadLeft/DpadRight | 按下方向高亮 |
| ABXY 按钮 | A/B/X/Y | 按下高亮 |
| 肩键 | LB/RB | 按下高亮 |
| 扳机 | LT/RT | 带填充进度条，按值（0~1）填充 |
| 中央按钮 | Back/Start | 按下高亮 |
| 遮罩 | connected=false | 未连接时显示遮罩层 |

**（2）轴数据显示**

LX / LY / RX / RY 四列数值，水平排列，轴值显示 2 位小数。

**（3）通信频率控制**

- 滑块：范围 10–60 Hz
- 数值显示：当前频率值
- 调用 `GET/POST /api/controller/frequency`

**（4）按键映射发送开关**

- `el-switch` 开关
- 说明文字：开启后手柄状态会自动按 JSON 格式发送到网络对端

#### 2.1.3 左栏 - 录制面板（RecordingPanel）

标签页：**录制控制** / **录制列表**

**（1）录制控制标签页**

| 元素 | 说明 |
|------|------|
| 录制按钮组 | 开始 / 暂停 / 继续 / 停止（按状态启用/禁用） |
| 录制名称输入框 | 开始录制时填写 |
| 录制时长显示 | 格式 `MM:SS.mmm` |
| 帧计数显示 | 已录制帧数 |

**（2）回放控制区**（位于录制控制标签页内）

| 元素 | 说明 |
|------|------|
| 播放 / 暂停 / 继续 / 停止按钮 | 按回放状态启用/禁用 |
| 进度条 | 可拖动跳转，调用 `POST /api/playback/seek` |
| 速度选择 | 0.5x / 1x / 2x |
| 禁止真手柄开关 | `el-switch`，开启后回放期间屏蔽真手柄输入 |

**（3）录制列表标签页**

| 元素 | 说明 |
|------|------|
| 录制项列表 | 每项展示：名称、时长、帧数、创建时间 |
| 每项操作按钮 | 播放 / 重命名 / 删除 / 导出 |
| 导入配置按钮 | 位于列表顶部，调用 `POST /api/recording/import` |

#### 2.1.4 中栏 - 网络面板（NetworkPanel）

自适应宽度。

**（1）客户端模式标签页**

| 元素 | 说明 |
|------|------|
| 表单 | 目标 IP、端口、协议（UDP/TCP 单选） |
| 连接 / 断开按钮 | 调用 `POST /api/network/connect` / `disconnect` |
| 重连状态显示 | 重连次数、倒计时 |
| 数据发送区（DataSender） | 见下方通用说明 |

**（2）服务端模式标签页**

| 元素 | 说明 |
|------|------|
| 表单 | 监听端口、最大客户端数 |
| 启动 / 停止按钮 | 调用 `POST /api/server/start` / `stop` |
| 客户端列表 | 展示已连接客户端 |
| 数据发送区（DataSender） | 见下方通用说明 |

**（3）数据发送区（DataSender）通用规范**

| 元素 | 说明 |
|------|------|
| 格式选择 | 文本 / 十六进制，水平排列单选 |
| 编码选择 | UTF-8 / GBK 下拉 |
| textarea 输入框 | 多行文本输入 |
| 字符 / 字节计数 | 实时显示当前输入字符数与字节数 |
| 发送按钮 | 支持 `Ctrl+Enter` 快捷键发送 |

#### 2.1.5 右栏 - 日志面板（LogPanel）

栏宽 380px。

**（1）通信日志标签页**

工具栏（顶部）：

| 控件 | 说明 |
|------|------|
| 显示发送 | checkbox，过滤方向=send |
| 显示接收 | checkbox，过滤方向=recv |
| 显示自动发送 | checkbox，过滤 auto=true |
| 显示原始 JSON | checkbox，切换显示模式 |
| 自动滚动 | checkbox，开启后自动滚动至最新 |

日志列表项格式：

- **时间戳**：`HH:MM:SS.mmm`
- **方向箭头**：发送 `↑` / 接收 `↓`（建议用颜色区分）
- **数据内容**：
  - 原始 JSON 开启时：显示原始 JSON 字符串
  - 原始 JSON 关闭时：显示解析后格式，例如：
    - `[按键] A,B`
    - `[摇杆] LX:0.50`
    - `[扳机] LT:0.75`

**（2）系统日志标签页**

| 元素 | 说明 |
|------|------|
| 级别过滤 | INFO / WARN / ERROR 多选 |
| 清空按钮 | 清空当前显示日志 |
| 日志列表 | 每条含时间戳、级别、消息 |

---

### 页面 2：手柄配置页（ControllerConfigPage）

- **路由**：`/config`

#### 2.2.1 顶部卡片

| 元素 | 说明 |
|------|------|
| 返回按钮 | 返回 Dashboard |
| 标题 | "手柄映射配置" |
| 按钮组 | 刷新手柄状态、手动重连手柄、导入配置、导出配置、重置默认 |

#### 2.2.2 左侧 - 手柄可视化（ControllerVisualizer）

实时手柄状态图形展示（与 Dashboard 中手柄可视化区域规范一致）。

#### 2.2.3 左侧 - 实时输入状态卡片

| 模块 | 说明 |
|------|------|
| 轴数据网格 | LX / LY / RX / RY，每项带进度条（-1~1 区间，居中为 0） |
| 扳机数据 | LT / RT，每项带进度条（0~1，显示百分比） |
| 按键状态网格 | 14 个按键指示灯，按下时点亮 |

#### 2.2.4 右侧 - 按键映射配置

**重要：直接展开显示，不使用折叠面板。**

14 个按键的映射配置，每个按键一行（或一卡片）：

按键列表：`A` / `B` / `X` / `Y` / `LB` / `RB` / `Back` / `Start` / `LS` / `RS` / `DpadUp` / `DpadDown` / `DpadLeft` / `DpadRight`

每个按键包含：

| 元素 | 说明 |
|------|------|
| 按键名称标签 | 显示按键名 |
| 发送内容输入框 | 文本输入 |
| 格式选择 | 文本 / 十六进制 |
| 测试按钮 | 按下该按键触发一次发送测试 |

---

## 三、API 对照表

### 3.1 HTTP API

基础地址：`http://localhost:8000`

| 方法 | 路径 | 功能 | 请求参数 | 响应 |
|------|------|------|----------|------|
| GET | `/api/version` | 获取版本信息 | - | `{name, version}` |
| POST | `/api/shutdown` | 关闭服务 | - | `{success}` |
| GET | `/api/controller/status` | 获取手柄状态 | - | `{buttons, axes, triggers, timestamp, connected, device_info, is_mock}` |
| POST | `/api/controller/detect` | 强制检测手柄 | - | `{success, message}` |
| GET | `/api/controller/frequency` | 获取通信频率 | - | `{frequency}` |
| POST | `/api/controller/frequency` | 设置通信频率 | `{frequency: number}` | `{success}` |
| POST | `/api/network/connect` | 连接网络 | `{ip, port, protocol}` | `{success, message}` |
| POST | `/api/network/disconnect` | 断开网络 | - | `{success}` |
| POST | `/api/network/status` | 获取网络状态 | - | `{connected, reconnecting, ...}` |
| POST | `/api/network/stop-reconnect` | 停止重连 | - | `{success}` |
| POST | `/api/network/send` | 发送数据（客户端） | `{data, format, encoding}` | `{success}` |
| POST | `/api/server/start` | 启动服务端 | `{port, max_clients}` | `{success}` |
| POST | `/api/server/stop` | 停止服务端 | - | `{success}` |
| POST | `/api/server/status` | 获取服务端状态 | - | `{status, clients_count}` |
| POST | `/api/server/clients` | 获取客户端列表 | - | `{clients: []}` |
| POST | `/api/server/send` | 发送数据（服务端） | `{data, format, encoding}` | `{success}` |
| POST | `/api/recording/start` | 开始录制 | `{name}` | `{success, recording_id}` |
| POST | `/api/recording/pause` | 暂停录制 | - | `{success}` |
| POST | `/api/recording/resume` | 继续录制 | - | `{success}` |
| POST | `/api/recording/stop` | 停止录制 | - | `{success}` |
| POST | `/api/recording/list` | 获取录制列表 | - | `{recordings: []}` |
| POST | `/api/recording/get` | 获取录制详情 | `{recording_id}` | `{recording}` |
| POST | `/api/recording/rename` | 重命名录制 | `{recording_id, new_name}` | `{success}` |
| POST | `/api/recording/delete` | 删除录制 | `{recording_id}` | `{success}` |
| POST | `/api/recording/export` | 导出录制 | `{recording_id}` | `{json_data}` |
| POST | `/api/recording/import` | 导入录制 | `{json_data}` | `{success}` |
| POST | `/api/playback/start` | 开始回放 | `{recording_id, speed}` | `{success}` |
| POST | `/api/playback/pause` | 暂停回放 | - | `{success}` |
| POST | `/api/playback/resume` | 继续回放 | - | `{success}` |
| POST | `/api/playback/stop` | 停止回放 | - | `{success}` |
| POST | `/api/playback/seek` | 跳转回放进度 | `{progress: 0-1}` | `{success}` |
| POST | `/api/playback/speed` | 设置回放速度 | `{speed: number}` | `{success}` |
| POST | `/api/playback/mode` | 设置回放模式 | `{enabled, block_real_controller}` | `{success}` |

### 3.2 WebSocket 消息

连接地址：`ws://localhost:8000/ws`

| 消息类型 | 方向 | 数据结构 | 说明 |
|----------|------|----------|------|
| `controller_state` | 服务器 → 客户端 | `{buttons, axes, triggers, timestamp, connected, device_info, is_mock, is_playback}` | 手柄状态广播 |
| `network_data` | 服务器 → 客户端 | `{direction: "send"/"recv", timestamp, data, format, encoding, auto}` | 网络通信日志 |
| `server_data` | 服务器 → 客户端 | `{direction: "send"/"recv", timestamp, data, format, encoding, auto}` | 服务端通信日志 |
| `recording_state` | 服务器 → 客户端 | `{recording: {status, duration, frame_count}, playback: {status, progress, ...}}` | 录制/回放状态 |
| `system_log` | 服务器 → 客户端 | `{level, message, timestamp}` | 系统日志 |

### 3.3 手柄状态数据结构

```json
{
  "buttons": {
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
  "triggers": {
    "LT": 0.0, "RT": 0.0
  }
}
```

### 3.4 网络自动发送数据格式（JSON）

按键映射发送开关开启后，手柄状态按以下格式自动发送到网络对端：

```json
{
  "btns": {"A": false, "B": false, "X": false, "Y": false,
           "LB": false, "RB": false, "Back": false, "Start": false,
           "LS": false, "RS": false,
           "DpadUp": false, "DpadDown": false,
           "DpadLeft": false, "DpadRight": false},
  "axes": {"LX": 0.0, "LY": 0.0, "RX": 0.0, "RY": 0.0},
  "trigs": {"LT": 0.0, "RT": 0.0}
}
```

---

## 四、UI 元素清单

### 4.1 全局元素

| 元素 | 数量 | 说明 |
|------|------|------|
| 顶部状态栏 | 1 | 含标题、配置链接、WS 状态、关闭服务 |
| 路由导航 | 2 | `/` 与 `/config` 之间切换 |

### 4.2 Dashboard 页面元素

#### 4.2.1 手柄状态面板

| 元素 | 类型 | 数量 |
|------|------|------|
| 手柄可视化图形 | 自定义 SVG/Canvas | 1 |
| 左摇杆点位 | 可移动标记 | 1 |
| 右摇杆点位 | 可移动标记 | 1 |
| 方向键按键 | 可高亮按钮 | 4 |
| ABXY 按钮 | 可高亮按钮 | 4 |
| 肩键 | 可高亮按钮 | 2 |
| 扳机进度条 | 进度条 | 2 |
| 中央按钮 | 可高亮按钮 | 2 |
| 未连接遮罩 | 遮罩层 | 1 |
| 轴数值显示 | 文本 | 4 |
| 频率滑块 | range slider | 1 |
| 频率数值显示 | 文本 | 1 |
| 按键映射发送开关 | switch | 1 |

#### 4.2.2 录制面板

| 元素 | 类型 | 数量 |
|------|------|------|
| 标签页 | tabs | 2 |
| 录制按钮组 | button | 4 |
| 录制名称输入框 | input | 1 |
| 录制时长显示 | text | 1 |
| 帧计数显示 | text | 1 |
| 回放按钮组 | button | 4 |
| 回放进度条 | slider | 1 |
| 回放速度选择 | select/radio | 1 |
| 禁止真手柄开关 | switch | 1 |
| 录制项列表 | list | N |
| 录制项操作按钮 | button | 4 × N |
| 导入配置按钮 | button | 1 |

#### 4.2.3 网络面板

| 元素 | 类型 | 数量 |
|------|------|------|
| 标签页 | tabs | 2 |
| IP 输入框 | input | 1 |
| 端口输入框 | input | 1 |
| 协议选择 | radio | 2 |
| 连接/断开按钮 | button | 2 |
| 重连状态显示 | text | 1 |
| 监听端口输入框 | input | 1 |
| 最大客户端数输入框 | input | 1 |
| 启动/停止按钮 | button | 2 |
| 客户端列表 | list | N |
| 数据发送区 | 复合组件 | 2（客户端+服务端各一） |

#### 4.2.4 数据发送区（DataSender，每套含）

| 元素 | 类型 | 数量 |
|------|------|------|
| 格式选择（文本/十六进制） | radio | 2 |
| 编码选择（UTF-8/GBK） | select | 1 |
| 输入框 | textarea | 1 |
| 字符/字节计数 | text | 2 |
| 发送按钮 | button | 1 |

#### 4.2.5 日志面板

| 元素 | 类型 | 数量 |
|------|------|------|
| 标签页 | tabs | 2 |
| 显示发送 checkbox | checkbox | 1 |
| 显示接收 checkbox | checkbox | 1 |
| 显示自动发送 checkbox | checkbox | 1 |
| 显示原始 JSON checkbox | checkbox | 1 |
| 自动滚动 checkbox | checkbox | 1 |
| 日志列表项 | list item | N |
| 级别过滤 | multi-select | 1 |
| 清空按钮 | button | 1 |

### 4.3 手柄配置页面元素

| 元素 | 类型 | 数量 |
|------|------|------|
| 返回按钮 | button | 1 |
| 标题 | text | 1 |
| 刷新手柄状态按钮 | button | 1 |
| 手动重连手柄按钮 | button | 1 |
| 导入配置按钮 | button | 1 |
| 导出配置按钮 | button | 1 |
| 重置默认按钮 | button | 1 |
| 手柄可视化 | 自定义图形 | 1 |
| 轴数据进度条 | progress | 4 |
| 扳机数据进度条 | progress | 2 |
| 按键状态指示灯 | indicator | 14 |
| 按键映射配置行 | 复合行 | 14 |
| 发送内容输入框 | input | 14 |
| 格式选择 | select | 14 |
| 测试按钮 | button | 14 |

---

## 五、设计要求

### 5.1 配色方案

**不限制配色方案**，设计 AI 可自由发挥。建议考虑以下语义化状态色：

- 连接成功 / 已连接：绿色系
- 连接中 / 等待：黄色系
- 断开 / 错误：红色系
- 录制中：醒目强调色（建议红/橙）
- 回放中：区分于录制的强调色（建议蓝/紫）

### 5.2 响应式布局

支持三个断点：

| 断点 | 最小宽度 | 布局调整建议 |
|------|----------|--------------|
| 大屏 | ≥ 1400px | 三栏水平排列（340 / 自适应 / 380） |
| 中屏 | 1200px–1400px | 三栏保持，可适度压缩间距 |
| 小屏 | 900px–1200px | 可改为两栏或单栏堆叠，面板内部滚动 |

### 5.3 三栏布局规范（Dashboard）

- **左栏**：固定 340px，垂直堆叠手柄状态面板 + 录制面板
- **中栏**：自适应填充剩余空间，承载网络面板
- **右栏**：固定 380px，承载日志面板
- **顶部状态栏**：横跨三栏，固定高度

### 5.4 实时性要求

- 手柄状态、网络日志、系统日志、录制/回放状态均通过 WebSocket 实时更新
- 状态更新应流畅，避免明显卡顿（建议高频更新时使用节流/虚拟列表）
- 日志列表高频写入时不应阻塞主交互

### 5.5 滚动行为

- **Dashboard 页面**：页面整体不滚动，各面板内部独立滚动
- **手柄配置页**：页面可整体滚动
- 日志面板：内部纵向滚动，工具栏固定

### 5.6 可交互元素状态

所有按钮、开关、滑块需具备明确的交互状态视觉反馈：

| 状态 | 视觉表现建议 |
|------|--------------|
| 默认 | 常规样式 |
| 悬停 | 颜色加深 / 边框高亮 / 阴影 |
| 按下 | 颜色更深 / 轻微缩放 |
| 禁用 | 灰化 / 降低不透明度 / cursor: not-allowed |
| 加载中 | 加载动画 / spinner |
| 激活/选中 | 强调色填充 |

### 5.7 状态指示规范

| 场景 | 指示方式 |
|------|----------|
| WebSocket 连接状态 | 颜色圆点 + 文字（已连接/连接中/已断开） |
| 手柄连接状态 | 可视化区域遮罩 + 文字提示 |
| 网络连接状态 | 颜色指示 + 连接信息 |
| 录制状态 | 录制按钮变色 + 时长闪烁 |
| 回放状态 | 进度条 + 状态文字 |
| 服务端运行状态 | 启动/停止按钮状态 + 客户端计数 |

### 5.8 数据格式规范

| 数据类型 | 显示格式 | 示例 |
|----------|----------|------|
| 时间戳 | `HH:MM:SS.mmm` | `14:23:45.678` |
| 录制时长 | `MM:SS.mmm` | `01:23.456` |
| 轴值 | 2 位小数 | `0.50`、`-0.75` |
| 扳机值 | 百分比 | `75%` |
| 回放进度 | 0–1 浮点 / 百分比 | `0.45` 或 `45%` |
| 频率 | 整数 + 单位 | `30 Hz` |

### 5.9 交互细节

- **快捷键**：数据发送区支持 `Ctrl+Enter` 快捷发送
- **进度条**：回放进度条支持拖动跳转
- **拖动**：录制列表项可考虑支持上下拖动排序（可选）
- **防误触**：删除录制、关闭服务等危险操作需二次确认
- **空状态**：录制列表、客户端列表、日志列表为空时需展示空状态提示

### 5.10 字体与可读性

- 等宽字体应用于：日志内容、轴数值、时间戳、十六进制数据
- 中文字体：系统默认中文字体栈
- 英文/数字：建议使用系统无衬线字体栈
- 日志区域字号建议略小（12–13px）以提升信息密度

---

## 六、附录

### 6.1 14 个按键完整列表

| 序号 | 按键名 | 类别 |
|------|--------|------|
| 1 | A | 主按键 |
| 2 | B | 主按键 |
| 3 | X | 主按键 |
| 4 | Y | 主按键 |
| 5 | LB | 肩键 |
| 6 | RB | 肩键 |
| 7 | Back | 中央按钮 |
| 8 | Start | 中央按钮 |
| 9 | LS | 摇杆按下 |
| 10 | RS | 摇杆按下 |
| 11 | DpadUp | 方向键 |
| 12 | DpadDown | 方向键 |
| 13 | DpadLeft | 方向键 |
| 14 | DpadRight | 方向键 |

### 6.2 轴与扳机列表

| 名称 | 类别 | 范围 | 显示格式 |
|------|------|------|----------|
| LX | 左摇杆 X 轴 | -1.0 ~ 1.0 | 2 位小数 |
| LY | 左摇杆 Y 轴 | -1.0 ~ 1.0 | 2 位小数 |
| RX | 右摇杆 X 轴 | -1.0 ~ 1.0 | 2 位小数 |
| RY | 右摇杆 Y 轴 | -1.0 ~ 1.0 | 2 位小数 |
| LT | 左扳机 | 0.0 ~ 1.0 | 百分比 |
| RT | 右扳机 | 0.0 ~ 1.0 | 百分比 |

### 6.3 协议与端口默认值参考

| 项 | 默认值 |
|------|--------|
| HTTP 端口 | 8000 |
| WebSocket 路径 | `/ws` |
| 通信频率默认值 | 30 Hz |
| 通信频率范围 | 10–60 Hz |
| 回放速度选项 | 0.5x / 1x / 2x |
| 编码选项 | UTF-8 / GBK |
| 数据格式选项 | 文本 / 十六进制 |

---

**文档结束**

> 设计 AI 可基于本文件自由进行视觉创作。除上述明确约束（如布局尺寸、滚动行为、数据格式、交互状态）外，配色、字体风格、图形风格、动画效果等均可自由发挥。
