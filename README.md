# 交叉实验顺序平衡 API（Crossover Experiment Order Balancing API）

基于 **Python 3.11 + FastAPI + SQLite** 的服务：创建交叉实验时提交互异条件、受试者 ID 与随机种子，
服务生成 **Williams 平衡拉丁方序列**并分配给受试者。

## 平衡性质

完整序列组（一个区组）保证：

1. **位置平衡**：每个条件在每个序列位置上出现的次数相等；
2. **相邻对平衡（残留效应平衡）**：每一个有向相邻条件对 `A → B` 出现的次数相等。

区组大小（每个完整序列组的序列条数，也是受试者数量的最小单位）：

- 条件数 **n 为偶数**：序列组含 **n 条**；
- 条件数 **n 为奇数**：单一方格无法同时满足两类平衡，序列组含 **2n 条**
  （n 条主序列 + 每条的镜像）。

受试者数量必须是区组大小的正整数倍；否则返回 **HTTP 422**，并在响应体中给出
最接近的可接受数量（`nearest_lower` / `nearest_upper` / `nearest_acceptable`）。

## 一条命令启动

需要 Docker 与 Docker Compose v2：

```bash
docker compose up --build
```

容器启动时会：

1. 安装 `requirements.txt` 中的依赖（镜像构建时已预装，启动时执行幂等校验）；
2. 启动 Uvicorn，应用在启动阶段自动创建 SQLite 数据表（`experiments`、`allocations`）。

停止：`Ctrl+C`，或另开终端执行 `docker compose down`（数据保留在命名卷
`crossover-data` 中；`docker compose down -v` 会同时删除数据）。

## 必需配置

配置均可使用默认值，无需手工准备：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `DATABASE_PATH` | `/data/experiments.db`（容器内） | SQLite 数据库文件路径，目录自动创建 |
| `PORT`（宿主机映射源，见 compose） | `8000` | 宿主机映射端口，可用 `PORT=9000 docker compose up --build` 修改 |

数据通过 Docker 命名卷 `crossover-data` 持久化到 `/data`。

## 访问地址与端口

- 服务地址：<http://localhost:8000>
- 交互式文档（Swagger UI）：<http://localhost:8000/docs>
- ReDoc 文档：<http://localhost:8000/redoc>
- 健康检查：<http://localhost:8000/health>

## API 概览

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| `POST` | `/experiments` | 创建实验并生成分配 |
| `GET` | `/experiments` | 列出全部实验（摘要） |
| `GET` | `/experiments/{id}` | 查询单个实验及完整分配 |
| `GET` | `/experiments/{id}/allocations` | 仅查询某实验的受试者分配 |
| `GET` | `/health` | 健康检查 |

### 创建实验

请求体：

```json
{
  "conditions": ["placebo", "low", "medium", "high"],
  "subject_ids": ["S01", "S02", "S03", "S04"],
  "seed": 123
}
```

约束：

- `conditions`：至少 2 个，字符串非空且**互异**；
- `subject_ids`：至少 1 个，字符串非空且**互异**，数量必须为区组大小的整数倍；
- `seed`：任意整数随机种子。

成功返回 `201`，示例（节选）：

```json
{
  "id": "b1e0...",
  "conditions": ["placebo", "low", "medium", "high"],
  "block_size": 4,
  "complete_blocks": 1,
  "allocations": [
    {"subject_id": "S02", "sequence_index": 2, "sequence": ["high", "placebo", "medium", "low"]}
  ],
  "created_at": "2026-09-21T00:00:00+00:00"
}
```

### 受试者数量不成整组（422）

例如 4 个条件、5 名受试者：

```bash
curl -X POST http://localhost:8000/experiments \
  -H 'Content-Type: application/json' \
  -d '{"conditions":["A","B","C","D"],"subject_ids":["p1","p2","p3","p4","p5"],"seed":9}'
```

返回 `422`：

```json
{
  "detail": {
    "block_size": 4,
    "requested": 5,
    "nearest_lower": 4,
    "nearest_upper": 8,
    "nearest_acceptable": 8,
    "detail": "For 4 conditions the Williams design needs subjects in complete blocks of 4; received 5. Nearest acceptable counts: 4 / 8. Use 8 (or another positive multiple of 4)."
  }
}
```

当请求数量小于一个区组时 `nearest_lower` 为 `null`（例如 5 个条件时区组为 10）。

### 确定性

相同的条件集合、受试者集合与种子必定产生相同的“受试者 → 序列”分配
（分配只取决于集合内容与种子，与列表提交顺序无关）。重新提交相同请求会得到
不同的实验 `id`，但分配内容完全一致，可随时通过 `GET /experiments/{id}` 查询。

## 本地开发（不使用 Docker）

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

运行算法性质测试（仅依赖标准库）：

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖：n = 2…12 的位置平衡与有向相邻对平衡、偶数 n 条 / 奇数 2n 条结构、
最近可接受数量、同种子确定性以及不同种子产生不同分配。

## 项目结构

```
.
├── app/
│   ├── main.py        # FastAPI 路由与 422 校验
│   ├── williams.py    # Williams 平衡序列生成与受试者分配（纯函数）
│   ├── db.py          # SQLite 连接、建表与持久化
│   └── schemas.py     # Pydantic 请求/响应模型
├── tests/
│   └── test_williams.py
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh      # 启动时安装依赖并拉起服务（建表在应用启动阶段完成）
└── requirements.txt
```
