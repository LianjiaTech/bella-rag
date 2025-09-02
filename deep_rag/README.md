# Deep RAG - Plan and Solve Agent

Deep RAG 实现了一个基于 Planning and Solve 模式的智能agent，支持流式和非流式输出。拥有比传统RAG更优的效果

## 功能特性

- **智能计划制定**: 基于用户问题自动生成执行计划
- **步骤式执行**: 按计划逐步执行工具调用
- **动态重规划**: 根据执行结果动态调整计划
- **流式输出**: 实时推送执行进度和结果
- **错误处理**: 完善的异常处理和错误报告

## API 接口

### 通过设置rag_chat接口的请求参数mode为"deep-rag"

**接口地址**: `POST /api/rag/chat`

**请求参数**:
```json
{
    "query": "用户问题",
    "file_ids": ["文件ID列表"],
    "user": "用户ID",
    "model": "gpt-4o-mini",
    "strategy": "fast",
    "stream": true,
    "mode": "deep-rag"
}
```

**响应格式**: 
流式：
Server-Sent Events (SSE)，具体事件参考下述说明
```
Content-Type: text/event-stream
data: {"id": "session_id", "object": "plan.create", "plan": [...]}
data: {"id": "session_id", "object": "plan.step.start", "step": ...}
data: {"id": "session_id", "object": "plan.step.complete", "step": ...}
data: {"id": "session_id", "object": "plan.complete", "plan": [...]}
data: {"id": "session_id", "object": "message.delta", "delta": [...]}
```

非流式：
```json
{
    "content": [
        {
            "type": "text",
            "text": [
                {
                    "value": "在处理与"采购"相关的问题时，已通过file_search工具查询到相关文件列表并获取了第一页内容。由于任务2被标记为不需要执行，因此没有进一步读取文件内容。当前没有筛选到与问题直接相关的数据。",
                    "annotations": []
                }
            ]
        }
    ],
    "plan": {
        "steps": [
            {
                "description": "使用file_search工具查询与'采购'相关的文件列表，获取第一页内容",
                "status": 1,
                "order": 1,
                "dependencies": [],
                "step_result": "[\"当前步骤结果：\\n- 工具：file_search\\n- 输入：{'question': '采购', 'page': 1}\\n- 输出：[]\"]",
                "actions": [
                    {
                        "name": "file_search",
                        "params": {
                            "question": "采购",
                            "page": 1
                        }
                    }
                ]
            },
            {
                "description": "使用read_file工具读取从file_search获取的文件内容",
                "status": -1,
                "order": 2,
                "dependencies": [
                    1
                ]
            }
        ]
    }
}
```


## 流式事件类型

### 1. plan.create (计划创建)
计划制定完成后推送，包含完整的执行计划。

```json
{
    "id": "session_id",
    "object": "plan.create",
    "plan": [
        {
            "order": 1,
            "description": "使用file_search工具查询相关文件",
            "dependencies": []
        }
    ],
    "reasoning_content": ""
}
```

### 2. plan.step.start (步骤开始)
步骤开始执行时推送。

```json
{
    "id": "session_id",
    "object": "plan.step.start", 
    "step": {
        "order": 1,
        "actions": [
            {
                "name": "file_search",
                "params": {"question": "采购", "page": 1}
            }
        ]
    }
}
```

### 3. plan.step.complete (步骤完成)
步骤执行完成后推送。

```json
{
    "id": "session_id",
    "object": "plan.step.complete",
    "step": [
        {
            "step_order": 1,
            "actions": [...],
            "status": "success",
            "step_result": "执行结果"
        }
    ]
}
```

### 4. plan.update (计划更新)
重新制定计划后推送。

```json
{
    "id": "session_id",
    "object": "plan.update",
    "plan": [
        {
            "order": 1,
            "description": "任务描述",
            "status": 1,
            "dependencies": []
        }
    ]
}
```

### 5. plan.complete (计划完成)
所有计划执行完成后推送。

```json
{
    "id": "session_id",
    "object": "plan.complete",
    "plan": [...]
}
```

### 6. message.delta (消息增量)
流式输出结论内容时推送。

```json
{
    "id": "session_id",
    "object": "message.delta",
    "delta": [
        {
            "index": 0,
            "type": "text",
            "text": {
                "value": "增量文本",
                "annotations": []
            }
        }
    ]
}
```

### 7. error (错误)
发生错误时推送。

```json
{
    "id": "session_id",
    "object": "error",
    "error": {
        "code": "error_code",
        "type": "error_type",
        "message": "错误描述"
    }
}
```

### 8. heartbeat (心跳包) 🆕
**新增功能**: 为了防止长时间无数据传输导致的连接超时，系统会每隔10秒自动发送心跳包。

```json
{
    "id": "session_id",
    "object": "heartbeat",
}
```

**特性说明:**
- 心跳包每10秒发送一次
- 在流式输出期间自动发送，无需额外配置
- 防止因长时间计算导致的连接超时断开
- 客户端可以忽略心跳包，或用于连接状态监控

## 使用示例

### Python 客户端示例

```python
import json

import requests


# 流式请求
def stream_request():
    url = "http://localhost:8000/rag/chat"
    data = {
        "question": "新B5套餐9月份活动蜂窝大板升级价格是多少？",
        "file_ids": ["F123", "F456"],
        "user": "user123",
        "strategy": "fast",
        "model": "gpt-4o",
        "stream": True,
        "mode": "deep-rag"
    }

    response = requests.post(url, json=data, stream=True)
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = line[6:]  # 去掉 'data: ' 前缀
                event = json.loads(data)
                print(f"事件: {event['event']}")
                print(f"数据: {json.dumps(event, ensure_ascii=False, indent=2)}")
```


## 实现架构

```
PlanAndSolveStreamRunner
├── run_stream()           # 流式执行入口
├── run_non_stream()       # 非流式执行入口
├── _emit_plan_create()    # 发送计划创建事件
├── _emit_plan_step_start() # 发送步骤开始事件
├── _emit_plan_step_complete() # 发送步骤完成事件
├── _emit_plan_update()    # 发送计划更新事件
├── _emit_plan_complete()  # 发送计划完成事件
├── _emit_message_delta()  # 发送消息增量事件
└── _emit_error()          # 发送错误事件
```

## 注意事项

1. **流式连接**: 流式接口使用 Server-Sent Events
2. **错误处理**: 所有异常都会通过 `error` 事件推送，客户端需要处理这些错误
3. **超时设置**: 建议设置合理的请求超时时间，避免长时间等待
4. **资源管理**: 流式连接占用服务器资源，使用完毕后应及时关闭

## 故障排除

1. **连接断开**: 检查网络连接和服务器状态
2. **解析错误**: 确保正确处理 SSE 格式的数据
3. **权限问题**: 验证用户权限和文件访问权限
4. **模型调用失败**: 检查 LLM 服务配置和 API 密钥 