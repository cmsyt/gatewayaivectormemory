# 任务清单：Embedding 共享服务

## 1. config.py 添加常量
- [x] 在 `config.py` 添加 `EMBED_DEFAULT_PORT = 8900`

## 2. EmbeddingEngine 双模式改造
- [x] `__init__` 添加 `_server_url` 和 `_remote_failed` 属性
- [x] 添加 `is_remote` 属性
- [x] 修改 `load()` 远程模式跳过本地加载
- [x] 修改 `encode()` 远程模式走 HTTP
- [x] 添加 `_encode_remote()` 方法
- [x] 添加 `_encode_remote_batch()` 方法
- [x] 修改 `encode_batch()` 远程模式走 HTTP

## 3. embed-server HTTP 服务
- [x] 创建 `embedding/server.py`：EmbedHandler + run_embed_server
- [x] 实现 POST /encode 接口
- [x] 实现 POST /encode_batch 接口
- [x] 实现 GET /health 接口
- [x] 实现 --daemon 后台运行

## 4. CLI 子命令
- [x] `__main__.py` 添加 `embed-server` 子命令及参数（--port, --bind, --daemon）
- [x] 添加 `embed-server` 处理分支

## 5. 自测验证
- [x] 启动 embed-server，测试 /health、/encode、/encode_batch
- [x] 设置 EMBEDDING_SERVER_URL，验证 EmbeddingEngine 远程模式
- [x] 不设置 EMBEDDING_SERVER_URL，验证本地模式不受影响
- [x] 远程不可用时验证降级到本地
