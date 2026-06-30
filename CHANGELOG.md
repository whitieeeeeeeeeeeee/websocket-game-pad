# 更新日志

本项目所有重要变更将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
且本项目遵循 [语义化版本](https://semver.org/lang/zh-CN/) 规范。

## [1.7.1] - 2026-06-28

### 新增功能 (Added)

- 手柄连接检测优化（设备信息、快速扫描、错误重试、连接回调）
- TCP 服务端模式（多客户端支持、心跳检测、广播/单播）
- 客户端停止重试功能（重连状态显示、停止按钮）
- 网络配置面板重构（客户端/服务端双 Tab 模式）
- 手柄操作录制与回放功能（录制、暂停、回放、调速、进度跳转）
- 录制文件管理（列表、重命名、删除、导入导出）
- UI 参数化配置体系（颜色、间距、圆角、字体等）
- UI 缩放适配优化（75%~150% 缩放正常显示）
- 版本号统一管理（前后端同步、API 接口）
- 版本号自动升级机制（每次迭代 +0.5）

### 优化改进 (Changed)

- 网络状态 API 增强（重连次数、下次重连时间）
- 手柄状态推送增强（设备信息、连接状态）
- WebSocket 消息类型扩展（服务端状态、录制状态等）
- 图标和布局改为相对单位，适配不同缩放
- CSS 变量系统建立
- Tailwind 配置扩展

### 技术细节

#### 新增的文件

- `api/tcp_server.py` - TCP 服务端模块，多客户端管理、心跳检测
- `api/recorder.py` - 录制与回放管理器，录制文件管理
- `src/config/version.ts` - 前端版本配置统一管理模块
- `src/config/ui.ts` - UI 参数化配置模块（颜色、间距、圆角、字体等）
- `src/utils/ui.ts` - UI 工具函数
- `src/components/ControllerRecording.vue` - 手柄录制与回放控制面板组件
- `src/pages/ControllerConfigPage.vue` - 手柄配置页面

#### 主要修改的文件

- `api/main.py` - 新增 TCP 服务端、录制回放、版本号等 API 接口，WebSocket 消息扩展
- `api/controller.py` - 手柄连接检测优化，设备信息获取，连续失败重试，连接回调
- `api/network_service.py` - TCP 客户端重连优化、停止重试功能、网络状态增强
- `src/App.vue` - 侧边栏版本号、UI 缩放适配、布局优化
- `src/stores/app.ts` - 新增服务端状态、录制状态、回放状态管理
- `src/api/client.ts` - 新增服务端、录制、回放等 API 方法
- `src/types/index.ts` - 新增服务端、录制、回放等类型定义
- `src/style.css` - CSS 变量系统、全局样式优化
- `tailwind.config.js` - Tailwind 配置扩展，支持 CSS 变量
- `package.json` - 版本号更新为 1.7.1

## [v1.0.0] - 2025-03-26

### 新增功能 (Added)

1. **后端系统日志 WebSocket 实时推送** - 新增 `WebSocketLogHandler` 类，将系统日志通过 WebSocket 实时推送到前端
2. **前端系统日志面板** - 调试面板新增「系统日志」Tab，与通信日志分离，支持级别过滤和历史记录
3. **前端退出服务按钮** - 侧边栏新增「退出服务」按钮，调用后端 `/api/shutdown` 接口优雅停止服务
4. **TCP 自动重连机制** - 实现指数退避策略的自动重连，初始延迟 2 秒，最大延迟 30 秒
5. **TCP 心跳检测** - 30 秒超时检测，无数据接收时自动触发重连
6. **启动时管理员权限自动申请** - Windows UAC 自动提权，用于防火墙配置
7. **Windows 防火墙自动配置** - 启动时自动添加防火墙规则，允许 TCP 端口访问
8. **连接状态细化** - 新增四种状态：`disconnected` / `connecting` / `connected` / `reconnecting`

### 优化改进 (Changed)

1. **后端日志系统重构** - 从 `print` 语句全面迁移至 Python `logging` 模块，支持多级别日志
2. **前端 API 调用统一封装** - 新增 `src/api/client.ts`，统一管理所有 API 请求和 WebSocket 连接
3. **TypeScript 类型定义集中管理** - 新增 `src/types/index.ts`，集中定义所有接口类型
4. **WebSocket 连接管理优化** - 前端实现自动重连机制，断开后 3 秒自动尝试重连
5. **UI 全面优化** - 优化间距、颜色、动画效果，提升响应式布局体验
6. **后端错误处理统一** - 新增全局异常处理器，统一 HTTP 异常和未捕获异常的响应格式
7. **TCP 发送重试机制** - 发送遇到瞬时错误时自动重试一次，提升发送可靠性

### 技术细节

#### 主要修改的文件

- `api/main.py` - FastAPI 主应用，新增日志系统、WebSocket、shutdown 接口、全局异常处理
- `api/network_service.py` - 网络服务层，新增 TCP 重连、心跳检测、状态管理、发送重试
- `api/controller.py` - 手柄控制器，接入 logging 模块
- `start.py` - 启动脚本，新增管理员权限申请、防火墙配置
- `start.bat` - Windows 启动脚本，新增管理员权限申请
- `src/App.vue` - 主应用组件，新增退出服务按钮和服务关闭提示
- `src/components/DebugPanel.vue` - 调试面板，新增系统日志 Tab 分离
- `src/stores/app.ts` - Pinia 状态管理，新增 systemLogs、WebSocket 自动重连
- `src/style.css` - 全局样式优化

#### 新增的文件

- `src/api/client.ts` - API 客户端统一封装
- `src/types/index.ts` - TypeScript 类型定义集中管理
