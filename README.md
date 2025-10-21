💡 AI 驱动的技术创新机会分析系统

![alt text](https://img.shields.io/badge/License-MIT-yellow.svg)


![alt text](https://img.shields.io/badge/python-3.9+-blue.svg)

这是一个基于知识图谱和多智能体（Multi-Agent）系统的端到端解决方案，旨在从专利数据中自动挖掘和评估技术创新机会。系统通过构建全面的专利知识图谱，并利用多个专门的 AI 智能体进行协同分析，最终生成一份高度可信、论证充分的战略决策报告。

🚀 核心功能

自动化知识抽取: 从 Excel 格式的专利数据中，自动抽结构化信息（如申请人、IPC分类号）和非结构化信息（利用 LLM 从摘要中提取技术原理、创新点、待解决问题等）。

知识图谱构建: 将抽取出的信息融合到 Neo4j 图数据库中，构建一个包含专利、公司、技术、发明人等多维度关系的知识网络。

混合式 RAG 基础: 将知识图谱的关键信息序列化并向量化存储到 ChromaDB 中，为后续的语义检索提供高效支持。

多智能体协同分析: 使用 LangGraph 框架编排一个由多个专家 Agent 组成的分析团队（例如，关联技术分析师、技术空白分析师、评审员、战略决策师），对特定技术领域进行深度剖析。

交互式 Web 应用: 通过 Streamlit 提供一个用户友好的界面，用户只需输入一个技术主题，即可启动整个分析流程并查看最终的决策报告。

高度可解释的报告: 最终生成的报告不仅给出结论，还清晰地展示了识别机会的证据来源、量化评估过程和打分理由，确保决策者能够理解和信任。

📊 系统架构与工作流程

整个系统分为两个主要阶段：离线数据处理 和 在线分析应用。

code
Mermaid
download
content_copy
expand_less
graph TD
    subgraph "Phase 1: 离线数据处理与知识库构建 (Offline Pipeline)"
        A[专利数据 patents.xlsx] -->|结构化抽取| B(excel_to_json_Structured.py);
        A -->|LLM非结构化抽取| C(excel_to_json_Unstructured.py);
        B --> D{structured_data.json};
        C --> E{unstructured_data.json};
        D & E --> F(json_to_neo4j.py);
        F --> G[(Neo4j 知识图谱)];
        G --> H(vectorize_full_kg.py);
        H --> I[(ChromaDB 向量库)];
    end

    subgraph "Phase 2: 在线分析与交互 (Online Application)"
        J(User) -- 1. 输入技术主题 --> K{Streamlit UI (ui.py)};
        K -- 2. 语义检索 --> I;
        I -- 3. 返回相关专利列表 --> K;
        J -- 4. 确认专利列表 --> K;
        K -- 5. 启动分析 --> L{LangGraph Multi-Agent System (main.py)};
        L -- 6. 调用工具查询 --> G;
        L -- 7. 生成最终报告 --> K;
        K -- 8. 展示报告 --> J;
    end
🛠️ 技术栈

数据处理: Pandas

知识图谱数据库: Neo4j

向量数据库: ChromaDB

AI / LLM 框架: LangChain, LangGraph

LLM / Embedding 模型: OpenAI / Dashscope (通义千问)

Web 应用框架: Streamlit

环境管理: python-dotenv

⚙️ 安装与配置

在开始之前，请确保您已经安装了 Python 3.9+。

1. 克隆项目仓库

code
Bash
download
content_copy
expand_less
git clone https://github.com/your-username/your-repository-name.git
cd your-repository-name

2. 创建虚拟环境并安装依赖

code
Bash
download
content_copy
expand_less
python -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

pip install -r requirements.txt 
# 如果没有 requirements.txt，请手动安装:
# pip install pandas openpyxl neo4j chromadb langchain langgraph langchain-openai streamlit python-dotenv numpy openai pydantic

3. 配置 Neo4j 数据库

确保您有一个正在运行的 Neo4j 实例（本地或云端均可），并准备好 URI、用户名和密码。

4. 设置环境变量

在项目根目录下创建一个名为 .env 的文件，并根据您的配置填充以下内容。这是保护您敏感信息的关键步骤。

code
Env
download
content_copy
expand_less
# Neo4j 数据库连接信息
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="your_neo4j_password"

# LLM 和 Embedding 模型 API Keys (以通义千问为例)
DASHSCOPE_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"

# 如果使用 OpenAI，请配置以下变量
# OPENAI_API_KEY="sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
# OPENAI_BASE_URL="https://api.openai.com/v1"

# ChromaDB 向量数据库配置
CHROMA_PERSIST_DIRECTORY="./chroma_db"
CHROMA_COLLECTION_NAME="patent_kg_collection"

注意: excel_to_json_Unstructured.py 和 vectorize_full_kg.py 文件中可能硬编码了 OPENAI_API_KEY 或 DASHSCOPE_API_KEY 的环境变量名，请确保 .env 文件中的键名与代码中的 os.getenv() 调用一致。

5. 准备输入数据

将您的专利数据文件命名为 patents.xlsx 并放置在项目根目录。该 Excel 文件必须至少包含以下列：

结构化信息: 申请号, 申请日, IPC分类号, 申请（专利权）人, 发明人, 发明名称, 代理人, 代理机构, 文献类型, 申请人所在国（省）

非结构化信息: 发明名称, 摘要

🏃‍♂️ 运行指南

请严格按照以下顺序执行脚本，以完成数据处理和知识库构建。

第一阶段：执行离线数据处理管道

抽取结构化数据

可在 excel_to_json_Structured.py 中配置 CONVERT_PARTIAL_DATA 来选择处理部分或全部数据。

code
Bash
download
content_copy
expand_less
python excel_to_json_Structured.py

抽取非结构化数据 (调用 LLM)

可在 excel_to_json_Unstructured.py 中配置 EXTRACT_PARTIAL_DATA 来选择处理部分或全部数据。此步骤耗时较长且会产生 API 调用费用。

code
Bash
download
content_copy
expand_less
python excel_to_json_Unstructured.py

构建知识图谱

code
Bash
download
content_copy
expand_less
python json_to_neo4j.py

向量化知识图谱 (调用 Embedding API)

此步骤也会产生 API 调用费用。

code
Bash
download
content_copy
expand_less
python vectorize_full_kg.py

完成以上步骤后，您的 Neo4j 数据库和 ChromaDB 向量库就已经准备就绪了。

第二阶段：启动在线分析应用

启动 Streamlit Web 服务

code
Bash
download
content_copy
expand_less
streamlit run ui.py

在浏览器中进行操作

打开浏览器并访问显示的 URL (通常是 http://localhost:8501)。

在侧边栏输入您感兴趣的技术主题（例如，“无人机电池快充技术”）。

点击“获取相关专利推荐”，系统将从向量库中检索相关专利。

在主界面确认或修改用于深度分析的专利列表。

点击“确认列表并启动深度分析”，等待多智能体系统完成分析。

查看最终生成的战略报告。

📂 文件说明

patents.xlsx: (示例) 输入的原始专利数据文件。

数据抽取脚本 (Data Extraction)

excel_to_json_Structured.py: 从 Excel 中提取预定义的结构化字段。

excel_to_json_Unstructured.py: 使用 LLM 从专利摘要中进行“填表式”知识抽取。

知识库构建脚本 (Knowledge Base Construction)

json_to_neo4j.py: 将 JSON 文件中的数据导入 Neo4j，构建知识图谱。

vectorize_full_kg.py: 查询 Neo4j，将关键信息向量化并存入 ChromaDB。

核心分析逻辑 (Core Analysis Logic)

tools.py: 定义了 AI Agent 可以使用的工具，如查询 Neo4j、进行语义检索、计算机会分数等。

main.py: 使用 LangGraph 定义和编排多智能体工作流的核心文件。

用户界面 (User Interface)

ui.py: 使用 Streamlit 构建的交互式 Web 应用前端。

.env: (需自行创建) 存储所有敏感配置和 API Keys。

📜 开源许可

本项目采用 MIT License 开源。
