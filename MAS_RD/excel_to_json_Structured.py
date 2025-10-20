# extract_structured_data.py (with Range Selection)

import pandas as pd
import os


def main():
    """
    读取 Excel 文件，只提取结构化字段，并保存为 JSON 文件。
    支持选择部分行进行转换。
    """
    # ==================== 配置区 ====================
    input_excel_file = "patents.xlsx"
    output_json_file = "structured_data_all.json"

    # 定义需要精确抽取的结构化字段列名
    columns_to_keep = [
        "申请号",
        "申请日",
        "IPC分类号",
        "申请（专利权）人",
        "发明人",
        "发明名称",
        "代理人",
        "代理机构",
        "文献类型",
        "申请人所在国（省）"
    ]

    # 是否只转换部分行？ (True / False)
    # 如果设为 False，将处理整个文件。
    CONVERT_PARTIAL_DATA = True
    # CONVERT_PARTIAL_DATA = False
    # 如果 CONVERT_PARTIAL_DATA = True，请设置以下范围
    # 注意：行号基于 Excel 中的 1-based 索引
    start_row = 1  # 开始行 (包含此行)
    end_row = 100  # 结束行 (包含此行)
    # ===============================================

    print("--- 脚本 1: 结构化数据抽取 ---")

    if not os.path.exists(input_excel_file):
        print(f"错误：找不到输入文件 '{input_excel_file}'")
        return

    try:
        print(f"正在读取 Excel 文件: '{input_excel_file}'...")
        df = pd.read_excel(input_excel_file, usecols=columns_to_keep)
        df = df.fillna('')
        print(f"成功从 '{input_excel_file}' 初步读取 {len(df)} 条记录。")

        # --- 新增：根据配置选择数据范围 ---
        if CONVERT_PARTIAL_DATA:
            if start_row > end_row or start_row < 1:
                print(f"错误：无效的行范围 ({start_row}-{end_row})。请检查配置。")
                return
            # 使用 .iloc 进行切片，注意 Python 是 0-based 索引
            df_to_process = df.iloc[start_row - 1: end_row]
            print(f"根据配置，将处理从第 {start_row} 行到第 {end_row} 行，共 {len(df_to_process)} 条记录。")
        else:
            df_to_process = df
            print(f"根据配置，将处理所有 {len(df_to_process)} 条记录。")

        print(f"正在将 {len(df_to_process)} 条数据保存到: '{output_json_file}'...")
        df_to_process.to_json(output_json_file, orient='records', indent=2, force_ascii=False)

        print(f"结构化数据抽取成功！文件已保存为 '{output_json_file}'")

    except KeyError as e:
        print(f"\n错误：列名 {e} 不存在。请检查 'columns_to_keep' 列表中的名称是否与 Excel 文件中的列标题完全一致。")
    except Exception as e:
        print(f"处理过程中发生错误: {e}")


if __name__ == "__main__":
    main()