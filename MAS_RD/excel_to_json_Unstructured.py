# extract_unstructured_data.py (Final Version: Aspect-based Extraction + Range Selection)

import pandas as pd
import os
import json
from dotenv import load_dotenv
from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError
from typing import Optional


# --- 1. Pydantic 模型 (保持不变) ---
class PatentAspects(BaseModel):
    object: Optional[str] = Field(None, description="发明对象: 发明所针对的核心产品、装置或方法。")
    problem: Optional[str] = Field(None, description="发明所需解决的问题: 发明旨在克服的技术难题、现有技术的缺陷。")
    innovation: Optional[str] = Field(None, description="创新点: 发明最核心、区别于现有技术的独特之处。")
    principle: Optional[str] = Field(None, description="原理知识: 解释发明如何工作的基本技术原理或科学依据。")
    benefit: Optional[str] = Field(None, description="效益知识: 发明带来的好处、优势或积极效果。")
    sub_functions: Optional[str] = Field(None, description="子功能: 发明包含的多个具体功能点，用分号';'隔开。")
    application: Optional[str] = Field(None, description="应用领域: 发明可以被应用到的具体场景或行业。")
    components: Optional[str] = Field(None, description="主要组件: 构成发明对象的关键物理部件，用分号';'隔开。")
    component_relations: Optional[str] = Field(None,
                                               description="组件之间的运动关系: 描述各组件如何相互连接、作用或运动。")
    technical_implementation: Optional[str] = Field(None,
                                                    description="技术实现知识: 实现功能的具体步骤、流程或技术方案。")


# --- 2. LLM 和环境设置 (保持不变) ---
def setup_llm_client():
    load_dotenv()
    try:
        client = OpenAI(
            api_key=os.getenv("DASHSCOPE_API_KEY"),
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        print("LLM 客户端初始化成功。")
        return client
    except Exception as e:
        print(f"初始化 LLM 客户端时出错: {e}")
        return None


# --- 3. 核心“填表式”知识抽取函数 (保持不变) ---
def extract_patent_aspects(text: str, client: OpenAI) -> dict | None:
    system_prompt = """
你是一位顶级的专利分析专家，任务是阅读一份专利摘要，并像填写一份结构化分析报告一样，抽取出其中定义的十个关键方面。

**抽取规则:**
1.  **全面分析**: 仔细阅读摘要，理解发明的核心内容。
2.  **精确对应**: 将文本信息精确地归类到以下十个字段中。
3.  **保持简洁**: 提取的文本应尽可能简洁、核心。
4.  **处理缺失信息**: 如果摘要中没有某个方面的信息，请在输出的 JSON 中省略该字段或将其值设为 null。
5.  **多值字段**: 对于 `sub_functions` 和 `components`，如果存在多个，必须用英文分号 ';' 将它们隔开。
6.  **严格的 JSON 输出**: 必须只返回一个严格符合规范的 JSON 对象，不要包含任何解释性文字。

**分析报告字段定义:**
- `object`: 发明对象 (装置、产品或方法的核心名称)。
- `problem`: 发明所需解决的问题 (现有技术的痛点)。
- `innovation`: 创新点 (最关键、独特的设计或思想)。
- `principle`: 原理知识 (工作背后的科学或技术原理)。
- `benefit`: 效益知识 (带来的优势、好处，如提升效率、降低成本)。
- `sub_functions`: 子功能 (多个功能用';'分隔)。
- `application`: 应用领域 (可以用在什么地方)。
- `components`: 主要组件 (构成产品的关键物理部分，多个用';'分隔)。
- `component_relations`: 组件之间的运动关系 (描述组件如何连接、互动)。
- `technical_implementation`: 技术实现知识 (实现的步骤或流程)。
"""
    try:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": text}]
        response = client.chat.completions.create(
            model="qwen3-max", messages=messages, response_format={"type": "json_object"}
        )
        response_json = json.loads(response.choices[0].message.content)
        validated_aspects = PatentAspects(**response_json)
        return validated_aspects.model_dump(exclude_none=True)
    except ValidationError as e:
        print(f"  错误: LLM 输出未通过 Pydantic 验证。错误信息:\n{e}\n  原始输出: {response_json}")
        return None
    except Exception as e:
        print(f"  错误：LLM 知识提取过程中发生未知错误。错误信息: {e}")
        return None


# --- 4. 主流程 (已重新加入范围选择功能) ---
def main():
    print("--- 脚本 2 (领域知识建模版 + 范围选择): 非结构化数据抽取 ---")

    # ==================== 配置区 ====================
    input_excel_file = "patents.xlsx"
    output_json_file = "unstructured_data_all.json"
    columns_to_read = ["发明名称", "摘要"]

    # 是否只抽取部分摘要？ (True / False)
    # 如果设为 False，将处理整个文件。
    EXTRACT_PARTIAL_DATA = True
    # EXTRACT_PARTIAL_DATA = False
    # 如果 EXTRACT_PARTIAL_DATA = True，请设置以下范围
    # 注意：行号基于 Excel 中的 1-based 索引
    start_row = 1  # 开始行 (包含此行)
    end_row = 100  # 结束行 (包含此行)
    # ===============================================

    llm_client = setup_llm_client()
    if not llm_client: return

    try:
        df = pd.read_excel(input_excel_file, usecols=columns_to_read)
        df = df.fillna('')
        print(f"成功从 '{input_excel_file}' 初步读取 {len(df)} 条记录。")
    except Exception as e:
        print(f"读取 Excel 文件时出错: {e}")
        return

    # --- 根据配置选择数据范围 ---
    if EXTRACT_PARTIAL_DATA:
        if start_row > end_row or start_row < 1:
            print(f"错误：无效的行范围 ({start_row}-{end_row})。请检查配置。")
            return
        df_to_process = df.iloc[start_row - 1: end_row]
        print(f"根据配置，将处理从第 {start_row} 行到第 {end_row} 行，共 {len(df_to_process)} 条记录。")
    else:
        df_to_process = df
        print(f"根据配置，将处理所有 {len(df_to_process)} 条记录。")

    all_extractions = []
    total_rows_to_process = len(df_to_process)
    for index, row in df_to_process.iterrows():
        patent_name = row["发明名称"]
        abstract_text = row["摘要"]

        print(
            f"\n--- [ 正在处理 Excel 第 {index + 2} 行 / 本次任务共 {total_rows_to_process} 条 ] 专利: '{patent_name}' ---")

        if not patent_name or not abstract_text:
            print("  跳过记录，缺少发明名称或摘要。")
            continue

        patent_aspects = extract_patent_aspects(abstract_text, llm_client)

        if patent_aspects:
            print(f"  分析报告提取并验证成功，包含 {len(patent_aspects)} 个方面。")
            record = {"发明名称": patent_name, "extracted_knowledge": patent_aspects}
            all_extractions.append(record)
        else:
            print("  未能从摘要中提取或验证分析报告。")

    print(f"\n正在将 {len(all_extractions)} 条分析报告保存到 '{output_json_file}'...")
    with open(output_json_file, 'w', encoding='utf-8') as f:
        json.dump(all_extractions, f, ensure_ascii=False, indent=2)

    print("非结构化数据(分析报告)抽取成功！")


if __name__ == "__main__":
    main()