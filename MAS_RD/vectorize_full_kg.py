import os
import sys
import chromadb
from openai import OpenAI
from neo4j import GraphDatabase
from dotenv import load_dotenv
from tqdm import tqdm
from typing import Dict, List, Any
import logging

# --- 0. 日志和基本配置 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
load_dotenv()

# --- 1. 加载环境变量和全局配置 ---

# Neo4j 配置
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USER")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD")

# OpenAI 配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
EMBEDDING_MODEL = "text-embedding-3-small"

# ChromaDB 配置
CHROMA_PERSIST_DIRECTORY = os.getenv("CHROMA_PERSIST_DIRECTORY")
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME")

# 处理批次大小
BATCH_SIZE = 64


# --- 2. 序列化函数 (与之前相同) ---
def serialize_patent_data(record: Dict[str, Any]) -> str:
    """将单条专利记录（字典格式）序列化为一段人类可读的描述性文本。"""
    title = record.get('patent_name') or '未知专利'
    company = record.get('company_name')
    innovations = record.get('innovations') or []
    problems = record.get('problems_solved') or []
    applications = record.get('application_areas') or []

    parts = []
    if company:
        base_info = f"专利“{title}”，由“{company}”申请。"
    else:
        base_info = f"专利“{title}”。"
    parts.append(base_info)

    if innovations:
        parts.append(f"其核心创新包括：{'、'.join(innovations)}。")
    if problems:
        parts.append(f"这项技术旨在解决“{'、'.join(problems)}”等问题。")
    if applications:
        parts.append(f"主要应用在{'、'.join(applications)}等领域。")

    return " ".join(parts)


# --- 3. 新增的验证函数 ---
def validate_config():
    """检查所有必需的环境变量是否已加载。"""
    required_vars = {
        "NEO4J_URI": NEO4J_URI,
        "NEO4J_USERNAME": NEO4J_USERNAME,
        "NEO4J_PASSWORD": NEO4J_PASSWORD,
        "OPENAI_API_KEY": OPENAI_API_KEY,
        "OPENAI_BASE_URL": OPENAI_BASE_URL,
        "CHROMA_PERSIST_DIRECTORY": CHROMA_PERSIST_DIRECTORY,
        "CHROMA_COLLECTION_NAME": CHROMA_COLLECTION_NAME,
    }

    missing_vars = [key for key, value in required_vars.items() if not value]

    if missing_vars:
        logging.error("=" * 50)
        logging.error("配置错误：缺少以下必要的环境变量。")
        for var in missing_vars:
            logging.error(f"  - {var}")
        logging.error("请检查您的 .env 文件是否完整且正确。")
        logging.error("=" * 50)
        sys.exit(1)  # 退出脚本

    logging.info("所有配置已成功加载。")


# --- 4. 主执行函数 ---
def main():
    """主函数，执行整个知识图谱向量化流程"""

    # 在执行任何操作前，首先验证配置
    validate_config()

    # --- 步骤 1: 连接 Neo4j 并执行精确查询 ---
    logging.info("\n步骤 1: 正在从 Neo4j 获取专利数据...")
    cypher_query = """
    MATCH (p:Patent)
    OPTIONAL MATCH (c:Company)-[:申请]->(p)
    OPTIONAL MATCH (p)-[:核心创新是]->(innovation_node:创新点)
    OPTIONAL MATCH (p)-[:旨在解决]->(problem_node:待解决问题)
    OPTIONAL MATCH (p)-[:应用于]->(application_node:应用领域)
    RETURN
        p.name AS patent_name,
        c.name AS company_name,
        collect(DISTINCT innovation_node.name) AS innovations,
        collect(DISTINCT problem_node.name) AS problems_solved,
        collect(DISTINCT application_node.name) AS application_areas
    """

    records = []
    try:
        with GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD)) as driver:
            driver.verify_connectivity()
            with driver.session(database="neo4j") as session:
                result = session.run(cypher_query)
                records = [record.data() for record in result]
        logging.info(f"  > 成功获取 {len(records)} 条专利记录。")
    except Exception as e:
        logging.error(f"  [错误] 无法连接到 Neo4j 或执行查询: {e}")
        return

    if not records:
        logging.warning("  [警告] 未从 Neo4j 获取到任何数据，脚本将退出。")
        return

    # --- 步骤 2: 序列化所有文本 ---
    logging.info("\n步骤 2: 正在将所有记录序列化为文本...")
    serialized_texts = [serialize_patent_data(rec) for rec in records]
    logging.info(f"  > 成功序列化 {len(serialized_texts)} 条文本。")

    # --- 步骤 3: 初始化 ChromaDB 和 OpenAI 客户端 ---
    logging.info("\n步骤 3: 正在初始化 ChromaDB 和 OpenAI 客户端...")
    try:
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIRECTORY)
        collection = chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"}
        )
        openai_client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        logging.info("  > ChromaDB 和 OpenAI 客户端初始化成功。")
    except Exception as e:
        logging.error(f"  [错误] 初始化客户端时出错: {e}")
        return

    # --- 步骤 4: 分批次向量化并存入 ChromaDB ---
    logging.info(f"\n步骤 4: 开始分批处理数据（每批 {BATCH_SIZE} 条）...")

    for i in tqdm(range(0, len(records), BATCH_SIZE), desc="向量化并存储批次"):
        # ... (后续代码与之前版本相同) ...
        batch_records = records[i:i + BATCH_SIZE]
        batch_texts = serialized_texts[i:i + BATCH_SIZE]

        try:
            response = openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=batch_texts
            )
            batch_embeddings = [item.embedding for item in response.data]

            batch_ids = []
            for j, rec in enumerate(batch_records):
                patent_name = rec.get('patent_name', f'missing_name_{i + j}')
                safe_name = "".join(x for x in patent_name if x.isalnum())[:50]
                batch_ids.append(f"patent_{i + j}_{safe_name}")

            batch_metadatas = [
                {
                    "patent_name": rec.get('patent_name', 'N/A'),
                    "company_name": rec.get('company_name', 'N/A')
                }
                for rec in batch_records
            ]

            collection.add(
                embeddings=batch_embeddings,
                documents=batch_texts,
                metadatas=batch_metadatas,
                ids=batch_ids
            )
        except Exception as e:
            logging.error(f"  [错误] 处理批次 {i // BATCH_SIZE + 1} 时出错: {e}")
            continue

    logging.info("\n🎉 全部处理完成！")
    logging.info(
        f"  > 总共有 {collection.count()} 个知识片段被成功向量化并存储在 ChromaDB 的 '{CHROMA_COLLECTION_NAME}' 集合中。")
    logging.info(f"  > 数据库文件存储在: {CHROMA_PERSIST_DIRECTORY}")


if __name__ == "__main__":
    main()