# ui.py

import streamlit as st
import pandas as pd
from main import app, GraphState
from tools import find_similar_patents

# --- 页面配置 ---
st.set_page_config(
    page_title="技术创新机会识别与评估系统",
    page_icon="💡",
    layout="wide"
)

# --- 初始化 Session State ---
if 'stage' not in st.session_state:
    st.session_state.stage = 'initial'
    st.session_state.tech_topic = ""
    st.session_state.recommended_patents = []
    st.session_state.confirmed_patents = []
    st.session_state.final_report = None


# --- 重置函数 ---
def reset_analysis():
    st.session_state.stage = 'initial'
    st.session_state.tech_topic = ""
    st.session_state.recommended_patents = []
    st.session_state.confirmed_patents = []
    st.session_state.final_report = None


# --- 界面布局 ---
st.title("💡 技术创新机会识别与评估系统")

with st.sidebar:
    st.header("分析设置")
    tech_topic = st.text_input(
        "请输入您想分析的技术主题：",
        placeholder="例如：风冷散热器",
        key='tech_topic_input'
    )

    if st.button("步骤 1: 获取相关专利推荐"):
        if tech_topic:
            with st.spinner('AI正在进行语义检索...'):
                recommended_list = find_similar_patents.run({"topic": tech_topic})

                if isinstance(recommended_list, list) and recommended_list and "错误" not in recommended_list[0]:
                    st.session_state.tech_topic = tech_topic
                    st.session_state.recommended_patents = recommended_list
                    st.session_state.confirmed_patents = recommended_list
                    st.session_state.stage = 'selection'
                    st.rerun()
                elif not recommended_list:
                    st.warning(f"未能找到与“{tech_topic}”相关的专利推荐。请尝试其他关键词。")
                else:
                    st.error(f"检索时发生错误: {recommended_list[0]}")
        else:
            st.sidebar.warning("请输入技术主题！")

    st.markdown("---")
    if st.button("开始新的分析"):
        reset_analysis()
        st.rerun()

# --- 主页面核心逻辑 ---
if st.session_state.stage == 'selection':
    st.subheader(f"步骤 2: 确认用于深度分析的专利列表")
    st.markdown(f"**分析主题:** `{st.session_state.tech_topic}`")
    st.info("以下是AI为您推荐的相关专利。您可以增删列表，然后启动深度分析。")

    confirmed_patents = st.multiselect(
        label="请确认或修改专利列表：",
        options=st.session_state.recommended_patents,
        default=st.session_state.recommended_patents
    )

    if st.button("✅ 确认列表并启动深度分析", type="primary"):
        if confirmed_patents:
            st.session_state.confirmed_patents = confirmed_patents
            st.session_state.stage = 'analysis'
            st.rerun()
        else:
            st.warning("请至少选择一个专利以进行深度分析。")

elif st.session_state.stage == 'analysis':
    with st.spinner('多智能体系统正在进行深度分析，这可能需要几分钟时间...'):
        initial_state = GraphState(
            patent_list=st.session_state.confirmed_patents,
            agent_outputs={},
            critique="",
            final_report=""
        )
        final_state = app.invoke(initial_state)
        st.session_state.final_report = final_state.get('final_report', "分析完成，但未生成报告。")
        st.session_state.stage = 'done'
        st.rerun()

elif st.session_state.stage == 'done':
    st.success(f"对 **{st.session_state.tech_topic}** 的分析已完成！")
    st.subheader("最终分析报告")
    st.markdown(st.session_state.final_report)

else:  # 'initial'
    st.info("👋 欢迎使用本系统！请在左侧侧边栏输入技术主题开始分析。")
    st.markdown("""
    #### 系统工作流程：
    1.  **输入主题**: 在左侧输入一个具体的技术主题。
    2.  **获取推荐**: 系统会利用AI检索并推荐一批高度相关的专利。
    3.  **专家确认**: 您可以基于自己的判断，从推荐列表中筛选出最终要分析的专利集合。
    4.  **深度分析**: 确认列表后，多智能体系统将启动，对选定的专利进行深度挖掘和评估，并生成最终报告。
    """)

    # 启动代码：streamlit run ui.py