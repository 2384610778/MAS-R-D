# build_knowledge_graph.py (Final Version: Application Date as a Node)

import os
import json
import re
from dotenv import load_dotenv
from neo4j import GraphDatabase


# --- 1. Neo4j 连接 (保持不变) ---
def setup_driver():
    """初始化 Neo4j 驱动程序。"""
    load_dotenv()
    uri = os.getenv("NEO4J_URI")
    user = os.getenv("NEO4J_USER")
    password = os.getenv("NEO4J_PASSWORD")
    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        driver.verify_connectivity()
        print("Neo4j 数据库连接成功。")
        return driver
    except Exception as e:
        print(f"连接 Neo4j 数据库时出错: {e}")
        return None


# --- 2. Cypher 辅助函数 (将 _create_node 恢复为简单版) ---
def _create_node(tx, label, properties: dict):
    """使用 MERGE 创建一个只带 name 属性的节点。"""
    query = f"MERGE (n:`{label}` {{name: $name}})"
    tx.run(query, name=properties.get("name"))


def _create_relationship(tx, source_label, source_name, target_label, target_name, rel_type):
    """使用 MERGE 创建关系，支持中文。"""
    query = (
        f"MATCH (a:`{source_label}` {{name: $source_name}}) "
        f"MATCH (b:`{target_label}` {{name: $target_name}}) "
        f"MERGE (a)-[r:`{rel_type}`]->(b)"
    )
    tx.run(query, source_name=source_name, target_name=target_name)


# --- 3. 核心函数 1: 构建图谱骨架 (已按新模型重写) ---
def build_structured_kg(patent_record: dict, driver: GraphDatabase.driver):
    """
    构建知识图谱的结构化部分，将“申请日”创建为一个独立的节点。
    """
    patent_name = patent_record.get("发明名称")
    if not patent_name: return

    application_date = patent_record.get("申请日")
    app_number = patent_record.get("申请号")
    applicant = patent_record.get("申请（专利权）人")
    inventors_str = patent_record.get("发明人", "")
    agents_str = patent_record.get("代理人", "")
    agency = patent_record.get("代理机构")
    doc_type = patent_record.get("文献类型")
    location = patent_record.get("申请人所在国（省）")
    ipc_str = patent_record.get("IPC分类号", "")

    inventors = [inv.strip() for inv in re.split(r'[;\s]+', inventors_str) if inv.strip()]
    agents = [agent.strip() for agent in agents_str.split() if agent.strip()]
    ipc_codes = [ipc.strip() for ipc in re.split(r'[;\s]+', ipc_str) if ipc.strip()]

    with driver.session() as session:
        # 步骤 1: 创建所有实体节点
        session.execute_write(_create_node, "Patent", {"name": patent_name})

        # --- 核心修改点 1: 创建 ApplicationDate 节点 ---
        if application_date:
            date_str = str(application_date).strip()
            session.execute_write(_create_node, "ApplicationDate", {"name": date_str})

        if app_number: session.execute_write(_create_node, "ApplicationNumber", {"name": app_number})
        if applicant: session.execute_write(_create_node, "Company", {"name": applicant})
        # ... (其余节点创建代码保持不变) ...
        if agency: session.execute_write(_create_node, "Agency", {"name": agency})
        if doc_type: session.execute_write(_create_node, "DocType", {"name": doc_type})
        if location: session.execute_write(_create_node, "Location", {"name": location})
        for inventor in inventors: session.execute_write(_create_node, "Person", {"name": inventor})
        for agent in agents: session.execute_write(_create_node, "Person", {"name": agent})
        for ipc in ipc_codes: session.execute_write(_create_node, "IPCNumber", {"name": ipc})

        # 步骤 2: 创建关系
        # --- 核心修改点 2: 创建 Patent 到 ApplicationDate 的关系 ---
        if application_date:
            date_str = str(application_date).strip()
            session.execute_write(_create_relationship, "Patent", patent_name, "ApplicationDate", date_str, "发明于")

        # 创建其他关系 (保持不变)
        if app_number: session.execute_write(_create_relationship, "Patent", patent_name, "ApplicationNumber",
                                             app_number, "申请号是")
        if applicant: session.execute_write(_create_relationship, "Company", applicant, "Patent", patent_name, "申请")
        # ... (其余关系创建代码与最终版完全相同，为简洁省略) ...
        if agency: session.execute_write(_create_relationship, "Agency", agency, "Patent", patent_name, "代理申请")
        if doc_type: session.execute_write(_create_relationship, "Patent", patent_name, "DocType", doc_type,
                                           "文献类型为")
        for inventor in inventors: session.execute_write(_create_relationship, "Person", inventor, "Patent",
                                                         patent_name, "发明")
        for agent in agents: session.execute_write(_create_relationship, "Person", agent, "Patent", patent_name, "经办")
        for ipc in ipc_codes: session.execute_write(_create_relationship, "Patent", patent_name, "IPCNumber", ipc,
                                                    "IPC分类为")
        if applicant:
            if location: session.execute_write(_create_relationship, "Company", applicant, "Location", location, "位于")
            if agency: session.execute_write(_create_relationship, "Company", applicant, "Agency", agency, "委托")
            for inventor in inventors: session.execute_write(_create_relationship, "Company", applicant, "Person",
                                                             inventor, "雇佣或受让")
        if agency:
            for agent in agents: session.execute_write(_create_relationship, "Agency", agency, "Person", agent, "指派")


# --- 4. 核心函数 2: 丰富图谱 (保持不变) ---
def enrich_kg_with_patent_aspects(llm_record: dict, driver: GraphDatabase.driver):
    patent_name = llm_record.get("发明名称")
    aspects_data = llm_record.get("extracted_knowledge")
    if not patent_name or not aspects_data: return

    key_to_graph_map = {
        "object": {"label": "发明对象", "rel": "研究对象是"},
        "problem": {"label": "待解决问题", "rel": "旨在解决"},
        "innovation": {"label": "创新点", "rel": "核心创新是"},
        "principle": {"label": "原理知识", "rel": "基于原理"},
        "benefit": {"label": "效益", "rel": "实现效益"},
        "sub_functions": {"label": "子功能", "rel": "包含功能"},
        "application": {"label": "应用领域", "rel": "应用于"},
        "components": {"label": "组件", "rel": "包含组件"},
        "component_relations": {"label": "组件关系", "rel": "组件间关系"},
        "technical_implementation": {"label": "技术实现", "rel": "实现方式是"}
    }

    with driver.session() as session:
        for key, value in aspects_data.items():
            if key not in key_to_graph_map: continue
            graph_model = key_to_graph_map[key]
            label = graph_model["label"]
            rel_type = graph_model["rel"]
            items = [item.strip() for item in value.split(';') if item.strip()] if key in ["sub_functions",
                                                                                           "components"] else [value]
            for item_name in items:
                session.execute_write(_create_node, label, {"name": item_name})
                session.execute_write(_create_relationship, "Patent", patent_name, label, item_name, rel_type)


# --- 5. 主函数 (保持不变) ---
def main():
    print("--- 脚本 3 (最终版 - 申请日为节点): 知识图谱构建 ---")

    neo4j_driver = setup_driver()
    if not neo4j_driver: return

    try:
        with open('structured_data_all.json', 'r', encoding='utf-8') as f:
            structured_data = json.load(f)
        print(f"成功加载 {len(structured_data)} 条结构化数据。")
        with open('unstructured_data_all.json', 'r', encoding='utf-8') as f:
            unstructured_data = json.load(f)
        print(f"成功加载 {len(unstructured_data)} 条非结构化(摘要)知识。")
    except FileNotFoundError as e:
        print(f"错误：找不到所需的数据文件 {e.filename}。请先运行脚本1和脚本2。")
        if neo4j_driver: neo4j_driver.close()
        return

    print("\n--- [阶段 1/2] 开始构建以“发明名称”为核心的图谱骨架 ---")
    for patent in structured_data:
        patent_name = patent.get("发明名称", "未知标题")
        print(f"  正在处理: '{patent_name}'")
        build_structured_kg(patent, neo4j_driver)
    print("知识图谱骨架构建完成。")

    print("\n--- [阶段 2/2] 开始将摘要知识汇入图谱 ---")
    for record in unstructured_data:
        patent_name = record.get("发明名称", "未知标题")
        print(f"  正在丰富: '{patent_name}'")
        enrich_kg_with_patent_aspects(record, neo4j_driver)
    print("知识图谱丰富完成。")

    print("\n--- 知识图谱构建任务全部完成 ---")
    neo4j_driver.close()


if __name__ == "__main__":
    main()