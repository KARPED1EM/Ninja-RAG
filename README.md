# Ninja RAG

🔥 **火影忍者知识库 RAG 系统** - 赛博朋克风格的混合检索问答系统

<div align="center">

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

**[快速开始](QUICKSTART.md)** | **[架构文档](docs/ARCHITECTURE.md)** | **[混合检索](docs/HYBRID_SEARCH.md)** | **[重构总结](REFACTOR_SUMMARY.md)**

</div>

---

## ✨ 特性

### 🔍 **混合检索系统**

- **稠密向量检索**: BGE-Large-ZH-v1.5 (1024维)
- **稀疏检索 BM25**: jieba 分词 + Okapi BM25 算法
- **RRF 融合**: Reciprocal Rank Fusion 混合排序
- **HyDE 增强**: 假设性文档嵌入（可选）

### 🧠 **知识图谱推理**

- Neo4j 图数据库
- 自动实体关系提取
- 多跳路径查询
- 图谱 + 向量混合 RAG

### 🎨 **赛博朋克 UI**

- Neo-Noir 霓虹美学设计
- 实时打字机效果
- SSE 流式进度反馈
- 全息扫描线动画
- 三大核心概念可视化

### ⚡ **智能同步**

- 基于 MD5 Hash 的增量同步
- 实时 SSE 进度显示
- 自动识别新增/更新/删除
- 清空知识库 & 重建功能

---

## 🚀 快速开始

### 一键启动（Windows）

```bash
# 1. 配置环境
copy .env.example .env
# 编辑 .env 填写 DASHSCOPE_API_KEY 和数据库密码

# 2. 运行启动脚本（自动检测并启动 Docker）
start.bat

# 3. 访问管理界面进行首次同步
# http://localhost:8000/admin
# 点击"同步知识库"，首次同步约 3-5 分钟

# 4. 开始查询
# http://localhost:8000/
```

### 手动部署

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境
cp .env.example .env
nano .env  # 填写 API Key 和数据库密码

# 3. 数据库迁移
uv run python scripts/migrate_add_hash.py

# 4. 启动服务
uv run python src/main.py

# 5. 访问应用
open http://localhost:8080/
```

详见 **[快速启动指南](QUICKSTART.md)**

### GPU 加速配置

```bash
# 1. 检测 GPU 支持
uv run python scripts/check_gpu.py

# 2. 如果有 GPU，编辑 .env
EMBEDDING_DEVICE="cuda"  # 或 cuda:0, cuda:1
EMBEDDING_BATCH_SIZE=64  # GPU 可用时增大批次

# 3. 安装 CUDA 版本的 PyTorch（如果需要）
uv pip install torch --index-url https://download.pytorch.org/whl/cu121
```

**性能对比**：
- CPU 模式：全量索引 1000 文档约 30-60 分钟
- GPU 模式：全量索引 1000 文档约 5-10 分钟（**5-10 倍提升**）

---

## 📊 架构概览

### 三层数据架构

```
源文档 (Raw)         已加载文档 (Loaded)      知识库 (Knowledge Base)
data/raw/wiki/   →   MySQL documents    →     Milvus 向量 + Neo4j 图谱
    ↑                      ↑                         ↑
用户管理            hash 比对基准            实际查询数据
```

### 混合检索流程

```
用户问题
    ↓
[可选] HyDE 生成假设答案
    ↓
┌─────────────┬─────────────┐
│ 稠密检索    │ 稀疏检索    │
│ BGE Vector  │ BM25 + jieba│
│ Top-10      │ Top-10      │
└─────────────┴─────────────┘
    ↓
RRF 融合排序
    ↓
Top-K 结果 → LLM 生成答案
```

### 技术栈

| 组件 | 技术 |
|------|------|
| **Web 框架** | FastAPI |
| **文档存储** | MySQL 8.0 |
| **向量数据库** | Milvus 2.3+ |
| **图数据库** | Neo4j 5.0+ |
| **嵌入模型** | BAAI/bge-m3 (多语言) |
| **稀疏检索** | BM25 + jieba |
| **LLM** | 通义千问 qwen-max |
| **前端** | Jinja2 + 纯 CSS/JS |
| **字体** | Orbitron + JetBrains Mono |

详见 **[架构文档](docs/ARCHITECTURE.md)**

---

## 🎨 界面预览

### 查询界面

<div align="center">

**赛博朋克霓虹美学 | 实时打字机效果 | 双面板检索来源**

</div>

- 🌃 深空黑底 + 霓虹青/品红双色系统
- ✨ 全息扫描线 + 六边形网格背景
- 💬 双色消息气泡（用户=青，AI=品红）
- 📊 置信度渐变进度条（红→黄→绿）
- 🔍 向量检索 + 图谱推理双面板
- 👁️ 查看完整上下文和提示词

### 管理界面

- 📁 三大核心概念可视化（源文档/已加载文档/知识库）
- ⚡ 统一同步操作（与源文档同步/增量同步）
- 🗑️ 危险操作防护（清空知识库/清空所有数据）
- 📟 实时日志终端（SSE 流式显示）
- 📚 文档列表（分类筛选 + 卡片网格）

---

## 📖 核心概念

### 源文档 (Raw Documents)

**定义**: `data/raw/wiki/` 目录下的原始 JSON 文件

**特点**:

- 用户手动管理（添加/修改/删除）
- 系统只读取用于比对
- 不可被系统修改

### 已加载文档 (Loaded Documents)

**定义**: MySQL `documents` 表中的结构化记录

**作用**:

- 增量同步的基准（对比 hash）
- 记录文档元数据
- 查询时展示文档信息

### 知识库 (Knowledge Base)

**定义**: Milvus 向量 + Neo4j 图谱

**作用**:

- Milvus: 向量检索（稠密 + 稀疏混合）
- Neo4j: 知识图谱关系推理
- 实际查询时使用的数据

---

## 🔄 工作流

### 添加新文档

```bash
# 1. 放入源文档
cp 新文档.json data/raw/wiki/角色/xxx/parse.json

# 2. 执行增量同步
http://localhost:8080/admin
点击"增量同步"

# 3. 系统自动识别
[INFO] 扫描完成: 发现 1 个新文档
[INFO] 处理中: 角色/xxx
[SUCCESS] 同步完成: 新增 1

# 4. 重建 BM25 索引（可选）
uv run python scripts/build_bm25_index.py
```

### 修改已有文档

```bash
# 1. 编辑源文档
nano data/raw/wiki/角色/漩涡鸣人/parse.json

# 2. 执行增量同步
http://localhost:8080/admin
点击"增量同步"

# 3. 系统检测 hash 变化
[INFO] 扫描完成: 发现 1 个更新
[INFO] 处理中: 角色/漩涡鸣人
[SUCCESS] 同步完成: 更新 1
```

### 重建知识库

```bash
# 场景: 修改了向量模型或图谱算法

# 1. 清空知识库（保留文档记录）
http://localhost:8080/admin
点击"清空知识库" → 确认

# 2. 重新同步
点击"与源文档同步"

# 3. 重建 BM25
uv run python scripts/build_bm25_index.py
```

---

## ⚙️ 配置优化

### 混合检索权重

```env
# 场景 1: 通用问答（推荐）
DENSE_WEIGHT=0.5
SPARSE_WEIGHT=0.5
USE_HYDE=false

# 场景 2: 强调专有名词精确匹配
DENSE_WEIGHT=0.3
SPARSE_WEIGHT=0.7

# 场景 3: 最大化检索质量（牺牲速度）
USE_HYDE=true  # 每次查询增加约 700ms
```

详见 **[混合检索文档](docs/HYBRID_SEARCH.md)**

---

## 📁 目录结构

```
ninja-rag/
├── data/raw/wiki/         # 源文档（用户管理）
├── .cache/bm25/           # BM25 索引缓存
├── src/
│   ├── api/               # API 层
│   ├── service/           # 应用服务层
│   ├── domain/            # 领域层
│   ├── data/              # 数据层
│   ├── infrastructure/    # 基础设施层
│   └── ui/templates/      # 前端模板
├── scripts/               # 工具脚本
├── docs/                  # 文档
│   ├── ARCHITECTURE.md    # 架构说明
│   └── HYBRID_SEARCH.md   # 混合检索文档
├── .env.example           # 配置模板
├── compose.yml            # Docker 配置
├── QUICKSTART.md          # 快速启动
└── REFACTOR_SUMMARY.md    # 重构总结
```

---

## 🌟 亮点功能

### 🎯 精确的增量同步

- **Hash 比对**: MD5 精确识别文件变化
- **避免误触发**: mtime 易变，hash 内容精确
- **SSE 实时进度**: 每个阶段实时反馈
- **低耦合设计**: raw 数据与处理逻辑分离

### 🔍 混合检索提升

| 检索方式 | 平均置信度 | Top-1 准确率 |
|----------|-----------|-------------|
| 单一稠密 | 0.42 | 65% |
| 稠密+稀疏 | **0.68** | **82%** |
| +HyDE | **0.75** | **88%** |

### 🎨 独特视觉设计

- **Neo-Noir 美学**: 银翼杀手 + 日本霓虹
- **全息效果**: 扫描线 + 六边形网格
- **霓虹光效**: 所有交互带光晕反馈
- **无框架依赖**: 纯 CSS/JS 实现

---

## 🐛 故障排查

### 同步失败

```bash
# 检查数据库连接
docker-compose ps
tail -f app.log

# 检查 Milvus
curl http://localhost:19530/healthz

# 检查 Neo4j
curl http://localhost:7474/
```

### 向量检索无结果

```bash
# 确认向量数量
http://localhost:8080/admin
查看"知识库"卡片

# 重建 BM25 索引
uv run python scripts/build_bm25_index.py
```

更多问题查看 **[快速启动指南](QUICKSTART.md#故障排查)**

---

## 📚 文档索引

- **[快速启动](QUICKSTART.md)**: 一步步部署指南
- **[架构说明](docs/ARCHITECTURE.md)**: 系统设计详解
- **[混合检索](docs/HYBRID_SEARCH.md)**: 检索策略说明
- **[重构总结](REFACTOR_SUMMARY.md)**: v2.0 重构详情

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

### 开发规范

- 遵循分层架构（UI → API → Service → Domain → Data）
- 使用 `uv` 管理依赖
- 所有用户界面文字使用中文
- 前端保持赛博朋克霓虑美学风格

---

## 📄 许可证

MIT License

---

## 🎯 路线图

- [ ] 支持多模态（图片、PDF）
- [ ] 分布式部署（Milvus 集群）
- [ ] 更多向量模型（ColBERT）
- [ ] 移动端适配
- [ ] 多语言支持

---

<div align="center">

**打造最酷的 RAG 系统 | 赛博朋克永不过时**

Made with 💠 by Ninja RAG Team

</div>
