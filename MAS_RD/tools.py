# tools.py (FIXED AGAIN)

import os
import datetime
from collections import Counter
from dotenv import load_dotenv
from langchain_core.tools import tool
from neo4j import GraphDatabase
import numpy as np
from openai import OpenAI
import chromadb
from pydantic import BaseModel, Field

# ... (所有环境变量和服务客户端初始化代码保持不变) ...
load_dotenv()
NEO4J_URI = os.getenv("NEO4J_URI")
# ... etc ...
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")
EMBEDDING_MODEL = "text-embedding-3-small"
openai_client_for_tools = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
chroma_client = chromadb.PersistentClient(path=os.getenv("CHROMA_PERSIST_DIRECTORY"))
chroma_collection = chroma_client.get_collection(name=os.getenv("CHROMA_COLLECTION_NAME"))


# --- 基础工具：数据库查询 (保持不变) ---
def run_cypher_query(query: str, params: dict = {}) -> list[dict]:
    # ... (此函数逻辑不变) ...
    driver = None
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(os.getenv("NEO4J_USER"), os.getenv("NEO4J_PASSWORD")))
        with driver.session() as session:
            result = session.run(query, params)
            return [record.data() for record in result]
    finally:
        if driver:
            driver.close()

# --- 语义检索工具 (已添加Docstring) ---
class SemanticSearchInput(BaseModel):
    topic: str = Field(description="The technical topic to search for similar patents.")

@tool(args_schema=SemanticSearchInput)
def find_similar_patents(topic: str, n_results: int = 15) -> list[str]:
    """
    Finds patents that are semantically similar to a given technical topic by searching in a vector database.
    Returns a list of patent names.
    """
    # ... (内部逻辑不变) ...
    try:
        response = openai_client_for_tools.embeddings.create(model=EMBEDDING_MODEL, input=[topic])
        query_vector = response.data[0].embedding
        results = chroma_collection.query(query_embeddings=[query_vector], n_results=n_results, include=["metadatas"])
        metadatas = results.get('metadatas', [[]])[0]
        if not metadatas:
            return []
        patent_names = [meta.get('patent_name', '未知专利名') for meta in metadatas]
        return patent_names
    except Exception as e:
        return [f"检索时发生错误: {e}"]

# ========================================================================
# vvv 核心分析工具 (已全部添加Docstring) vvv
# ========================================================================

class AnalysisInput(BaseModel):
    patent_list: list[str] = Field(description="A list of patent names to be analyzed.")

@tool(args_schema=AnalysisInput)
def find_associated_technologies(patent_list: list[str]) -> str:
    """
    Analyzes a list of patents to find other 'technical implementations' that frequently co-occur in the same application areas.
    The input must be a Python list of patent names.
    """
    if not patent_list: return "输入专利列表为空，无法进行关联技术分析。"
    query = """
    MATCH (p1:Patent)-[:应用于]->(scene:应用领域) WHERE p1.name IN $patent_list
    MATCH (scene)<-[:应用于]-(p2:Patent) WHERE NOT p2.name IN $patent_list
    MATCH (p2)-[:实现方式是]->(t:技术实现)
    RETURN t.name AS associated_tech, COUNT(DISTINCT p2) AS association_strength
    ORDER BY association_strength DESC LIMIT 10
    """
    try:
        results = run_cypher_query(query, {"patent_list": patent_list})
        if not results: return "在所选专利的应用领域内，未发现显著的其他关联技术。"
        formatted_parts = [f"{r['associated_tech']} (关联强度:{r['association_strength']})" for r in results]
        return f"基于所选的专利列表，关联最强的其他技术实现有：{', '.join(formatted_parts)}"
    except Exception as e: return f"查询关联技术过程中发生错误: {e}"

@tool(args_schema=AnalysisInput)
def get_technology_trend(patent_list: list[str]) -> str:
    """
    Analyzes the application year distribution of a list of patents to return quantitative growth metrics, such as linear regression slope.
    The input must be a Python list of patent names.
    """
    if not patent_list: return "输入专利列表为空，无法进行趋势分析。"
    query = """
    MATCH (p:Patent)-[:发明于]->(ad:ApplicationDate) 
    WHERE p.name IN $patent_list AND ad.name IS NOT NULL
    WITH substring(ad.name, 0, 4) AS year, COUNT(p) AS patent_count
    RETURN year, patent_count ORDER BY year ASC
    """
    try:
        results = run_cypher_query(query, {"patent_list": patent_list})
        if len(results) < 4: return "所选专利列表的有效年份数据不足4年，无法进行有意义的趋势分析。"
        data = [{'year': int(r['year']), 'patent_count': int(r['patent_count'])} for r in results if r['year'] and str(r['year']).isdigit()]
        if len(data) < 4: return "所选专利列表的有效年份数据不足4年，无法进行趋势分析。"
        years, counts = np.array([d['year'] for d in data]), np.array([d['patent_count'] for d in data])
        slope, _ = np.polyfit(years, counts, 1)
        return f"对所选专利列表的趋势分析完成。整体趋势的回归斜率: {slope:.2f}。"
    except Exception as e: return f"分析专利趋势过程中发生错误: {e}"

@tool(args_schema=AnalysisInput)
def find_technology_gaps(patent_list: list[str]) -> str:
    """
    Analyzes the 'problems to be solved' associated with a list of patents, and identifies which of these problems have the fewest technical solutions in the entire knowledge graph.
    The input must be a Python list of patent names.
    """
    if not patent_list: return "输入专利列表为空，无法进行技术空白分析。"
    query = """
    MATCH (p:Patent)-[:旨在解决]->(problem:待解决问题) WHERE p.name IN $patent_list
    WITH DISTINCT problem
    OPTIONAL MATCH (problem)<-[:旨在解决]-(:Patent)-[:实现方式是]->(tech:技术实现)
    WITH problem, COUNT(DISTINCT tech) AS tech_count
    OPTIONAL MATCH (problem)<-[:旨在解决]-(:Patent)-[:应用于]->(scene:应用领域)
    WITH problem, tech_count, scene, COUNT(scene) AS scene_freq
    ORDER BY problem.name, scene_freq DESC
    WITH problem, tech_count, COLLECT(scene.name)[0] AS top_scene
    RETURN problem.name AS problem_name, tech_count, COALESCE(top_scene, '暂无') AS top_scene_name
    ORDER BY tech_count ASC, problem_name ASC LIMIT 10
    """
    try:
        results = run_cypher_query(query, {"patent_list": patent_list})
        if not results: return "在所选专利涉及的问题域中，未发现明显的技术空白。"
        formatted_parts = [f"{i+1}. 问题：[{r['problem_name']}] (全图谱技术方案: {r['tech_count']})，主要领域：[{r['top_scene_name']}]" for i, r in enumerate(results)]
        return f"在所选专利涉及的问题域中，发现的潜在技术空白包括：{', '.join(formatted_parts)}"
    except Exception as e: return f"查找技术空白过程中发生错误: {e}"

@tool(args_schema=AnalysisInput)
def assess_technology_maturity(patent_list: list[str]) -> str:
    """
    Evaluates the overall maturity (nascent, growth, or mature stage) of the technology cluster represented by a list of patents.
    The input must be a Python list of patent names.
    """
    if not patent_list: return "输入专利列表为空，无法评估技术成熟度。"
    query = """
    MATCH (p:Patent)-[:发明于]->(ad:ApplicationDate) 
    WHERE p.name IN $patent_list AND ad.name IS NOT NULL
    RETURN substring(ad.name, 0, 4) AS year ORDER BY year ASC
    """
    try:
        results = run_cypher_query(query, {"patent_list": patent_list})
        if not results: return "未找到所选专利列表的任何有效年份数据。"
        years = [int(r['year']) for r in results if r['year'] and str(r['year']).isdigit()]
        if not years: return "所选专利列表的数据中没有有效的年份信息。"
        current_year, min_year = datetime.datetime.now().year, min(years)
        if min_year >= current_year - 2: return "所选专利集群的技术成熟度处于[萌芽期]。"
        # ... (其他成熟度判断逻辑) ...
        return "所选专利集群的技术成熟度处于[发展中期]。"
    except Exception as e: return f"评估技术成熟度过程中发生错误: {e}"

# --- MCDA工具 (也需要docstring) ---
class MCDAInput(BaseModel):
    hotness_score: float = Field(description="Score representing the trendiness of the topic, between 0.0 and 1.0.")
    gap_score: float = Field(description="Score representing the lack of solutions for the problem, between 0.0 and 1.0.")
    maturity_score: float = Field(description="Score representing the maturity of the technology, between 0.0 and 1.0.")
    maturity_stage: str = Field(description="A string describing the maturity stage, e.g., '成长期'.")

@tool(args_schema=MCDAInput)
def calculate_opportunity_score(hotness_score: float, gap_score: float, maturity_score: float, maturity_stage: str) -> float:
    """
    A multi-criteria decision analysis (MCDA) model that calculates a final opportunity score based on complex rules.
    It takes scores for hotness, gap, and maturity, plus a maturity stage string.
    """
    weights = {'hotness': 0.3, 'gap': 0.5, 'maturity': 0.2}
    scores = {'hotness': hotness_score, 'gap': gap_score, 'maturity': maturity_score}
    if not all(0.0 <= s <= 1.0 for s in scores.values()): raise ValueError("输入的各项评分必须在0.0到1.0之间。")
    base_score = sum(scores[k] * weights[k] for k in scores) * 100
    final_score = base_score
    if scores['hotness'] > 0.8 and scores['gap'] > 0.8:
        final_score += 20
    if '成熟期' in maturity_stage:
        final_score *= 0.5
    return round(max(0.0, min(100.0, final_score)), 2)