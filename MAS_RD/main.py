# main.py

import operator
from typing import TypedDict, List, Dict, Annotated
from functools import partial
import os
from dotenv import load_dotenv

from langchain_core.tools import Tool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END, START
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage

load_dotenv()

# --- 导入工具 ---
from tools import (
    find_associated_technologies,
    get_technology_trend,
    find_technology_gaps,
    assess_technology_maturity,
    calculate_opportunity_score
)


# --- 定义共享状态 ---
class GraphState(TypedDict):
    patent_list: List[str]
    agent_outputs: Annotated[dict, operator.or_]
    critique: str
    final_report: str


# --- LLM 和 Agent 创建逻辑 ---
llm = ChatOpenAI(model="qwen-max", temperature=0, api_key=os.getenv("DASHSCOPE_API_KEY"),
                 base_url="https://dashscope.aliyuncs.com/compatible-mode/v1")

GAP_AGENT_SYSTEM_PROMPT = "你是一位顶尖的风险投资分析师，你的投资哲学是寻找‘被忽视的角落’。你的任务是识别那些真正存在巨大市场痛苦，但尚未被主流技术很好满足的领域。请对所有数据保持批判性思维，你的最终目标是找到高风险、高回报的早期机会。"
EVALUATION_AGENT_SYSTEM_PROMPT = "你是一位经验丰富的企业技术战略顾问。你的任务是精确评估一项技术的商业化阶段，并为客户提供明确的进入或观望建议。请结合专利数据，严谨地分析其生命周期，并解释你的判断依据。"
CRITIC_AGENT_SYSTEM_PROMPT = "你是一个专业的评审员（Critic）。你的唯一任务是审查团队提交的初步分析报告，并从三个方面提出尖锐的、建设性的批评：1. 数据是否足够支撑结论？ 2. 这个机会是否存在被忽视的巨大风险？ 3. 这个分析是否存在逻辑漏洞或思维盲区？ 你的回答必须直接、简短、切中要害。"
DEFAULT_SYSTEM_PROMPT = "You are a helpful assistant. Use the provided tools to answer the user's request based on the provided input."


def create_agent_executor(tools: list[Tool], system_prompt: str = DEFAULT_SYSTEM_PROMPT) -> AgentExecutor:
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("user", "Please perform your analysis based on the following structured input: {input}"),
        ("placeholder", "{agent_scratchpad}"),
    ])
    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(agent=agent, tools=tools, verbose=True)


# --- 实例化专家 Agent ---
association_agent_executor = create_agent_executor([find_associated_technologies])
emerging_theme_agent_executor = create_agent_executor([get_technology_trend])
gap_agent_executor = create_agent_executor([find_technology_gaps], system_prompt=GAP_AGENT_SYSTEM_PROMPT)
evaluation_agent_executor = create_agent_executor(
    [assess_technology_maturity, calculate_opportunity_score],
    system_prompt=EVALUATION_AGENT_SYSTEM_PROMPT
)


# --- 定义图的节点 ---
def agent_node(state: GraphState, agent_executor: AgentExecutor, name: str) -> dict:
    print(f"\n--- Running {name} Agent (On Full Patent List) ---")
    patent_list = state.get('patent_list', [])
    if not patent_list:
        return {"agent_outputs": {name: "没有有效的专利可供分析。"}}

    result = agent_executor.invoke({"input": {"patent_list": patent_list}})

    return {"agent_outputs": {name: result['output']}}


association_agent_node = partial(agent_node, agent_executor=association_agent_executor, name="Association")
emerging_theme_agent_node = partial(agent_node, agent_executor=emerging_theme_agent_executor, name="EmergingTheme")
gap_agent_node = partial(agent_node, agent_executor=gap_agent_executor, name="TechnologyGap")


def critic_agent_node(state: GraphState) -> dict:
    print("\n--- Running Critic Agent ---")
    agent_outputs = state.get('agent_outputs', {})
    review_prompt = f"""
    以下三份报告是基于一个用户确认的专利列表生成的，请你进行严格审查。

    报告1: [关联技术分析师]\n{agent_outputs.get("Association", "无结果")}
    报告2: [新兴主题分析师]\n{agent_outputs.get("EmergingTheme", "无结果")}
    报告3: [风险投资分析师 - 专注技术空白]\n{agent_outputs.get("TechnologyGap", "无结果")}

    请根据你的角色要求，对以上报告提出你的批判性意见。
    """
    response = llm.invoke([SystemMessage(content=CRITIC_AGENT_SYSTEM_PROMPT), ("user", review_prompt)])
    return {"critique": response.content}


# vvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvvv
# --- 函数已根据您的要求完全更新 ---
def evaluation_agent_node_final(state: GraphState) -> dict:
    print("\n--- Running Final Evaluation Agent (Decision-Support Upgrade) ---")
    agent_outputs = state.get('agent_outputs', {})
    critique = state.get('critique', "无批判性意见。")
    patent_list = state.get('patent_list', [])

    # 使用您提供的全新、强调证据追溯和论证过程的指令模板
    evaluation_prompt = f"""
    你是一位顶级的技术战略分析师，你的最终交付物是一份能让CEO和CTO直接用于决策的、**高度可信且论证充分**的战略报告。

    --- 基础情报 ---
    这是你的团队基于一个核心专利列表（共{len(patent_list)}篇）提交的三份初步分析报告和一份内部评审意见：

    报告1: [关联技术分析师]\n{agent_outputs.get("Association", "无结果")}
    报告2: [新兴主题分析师]\n{agent_outputs.get("EmergingTheme", "无结果")}
    报告3: [风险投资分析师 - 专注技术空白]\n{agent_outputs.get("TechnologyGap", "无结果")}

    内部评审意见:\n{critique}
    --- END 基础情报 ---

    你的核心任务和行动步骤如下：

    **第一步：机会识别 (Opportunity Identification)**
    仔细阅读所有情报，识别出 2 到 3 个具体的、有潜力的技术创新机会点。

    **第二步：机会评估与论证 (Opportunity Evaluation & Justification)**
    对于你识别出的**每一个**机会点，你必须按顺序执行并清晰地展示你的完整分析过程：
    1.  **机会描述:** 清晰地定义这个机会点是什么。
    2.  **【关键】证据链接 (Evidence Linking):** **明确列出你是基于「基础情报」中的哪些具体发现才识别出这个机会的。在撰写此部分时，绝对不要使用‘报告1’、‘报告2’或‘报告3’这类内部代号。** 你应该直接引用或概括对应分析的核心发现。例如，你应该这样陈述：“该机会的识别主要基于**技术空白分析**所揭示的‘XX问题技术方案稀缺’这一发现，并结合了**关联技术分析**中它与‘YY技术’的强关联性。”
    3.  **成熟度评估:** 调用 `assess_technology_maturity` 工具进行评估，并**在报告中直接展示工具返回的评估结果**。
    4.  **量化打分与理由:**
        -   **Hotness (趋势性):** 给出一个0.0到1.0的分数，并**必须简述你的打分理由**（例如，“基于趋势分析，相关专利申请量的回归斜率为正值，显示出持续的研发热度，因此评分为0.7”）。
        -   **Gap (技术缺口):** 给出一个0.0到1.0的分数，并**必须简述你的打分理由**（例如，“技术空白分析明确指出了‘XX问题’是当前解决方案最少的领域，属于明显的技术缺口，因此评分0.9”）。
        -   **Maturity (成熟度):** 给出一个0.0到1.0的分数，并**必须简述你的打分理由**（例如，“工具评估结果为‘成长期’，意味着市场已初步验证但领导者尚未完全形成，是进入的理想窗口期，因此评分0.8”）。
    5.  **计算总分:** 调用 `calculate_opportunity_score` 工具计算最终得分，并**在报告中展示最终得分**。

    **第三步：生成具备高度可解释性的最终报告 (Final Report Generation)**
    请将你的完整分析过程整理成一份结构化的最终报告。报告必须严格遵循以下格式，确保最终用户能够轻松理解：
    - **执行摘要:** 对整体技术领域的宏观判断和核心机会的总结。
    - **核心创新机会清单:** (为每一个识别出的机会点生成以下模块)
        - **机会点 [编号]:** [机会点名称]
            - **分析与论证:**
                - **识别依据:** [在这里填入你在第二步第2点中写的、**对最终用户友好的证据链接**，不包含任何内部报告代号]
                - **成熟度评估:** [在这里填入你在第二步第3点中**工具返回的评估结果**]
            - **量化评估:**
                - 趋势性 (Hotness): **[分数]** - *理由: [在这里填入对用户友好的打分理由]*
                - 技术缺口 (Gap): **[分数]** - *理由: [在这里填入对用户友好的打分理由]*
                - 成熟度 (Maturity): **[分数]** - *理由: [在这里填入对用户友好的打分理由]*
            - **最终机会得分:** **[总分]** (满分100)
    - **综合战略建议:** 基于以上所有机会点的评估，给出1-2条最高优先级的战略建议，并简述这些建议是如何与上面的机会点分析相关联的。

    请现在开始你的分析和报告生成。
    """

    result = evaluation_agent_executor.invoke({"input": evaluation_prompt})
    return {"final_report": result['output']}


# --- 函数更新结束 ---
# ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^


# --- 组装 StateGraph ---
workflow = StateGraph(GraphState)

workflow.add_node("association_agent", association_agent_node)
workflow.add_node("emerging_theme_agent", emerging_theme_agent_node)
workflow.add_node("gap_agent", gap_agent_node)
workflow.add_node("critic_agent", critic_agent_node)
workflow.add_node("evaluation_agent", evaluation_agent_node_final)

# 定义工作流图
workflow.add_edge(START, "association_agent")
workflow.add_edge(START, "emerging_theme_agent")
workflow.add_edge(START, "gap_agent")

workflow.add_edge(["association_agent", "emerging_theme_agent", "gap_agent"], "critic_agent")
workflow.add_edge("critic_agent", "evaluation_agent")
workflow.add_edge("evaluation_agent", END)

app = workflow.compile()
print("\nStateGraph 编译成功!")