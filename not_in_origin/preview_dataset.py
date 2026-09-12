#!/usr/bin/env python3
"""
这个脚本用于查看dataset中每个数据文件的前5行内容，
并标注每部分数据来自哪个路径/文件。
输出结果将保存到指定的文件中。
"""

import os
import json
import pandas as pd
from pathlib import Path

def preview_data_files(dataset_path, output_file=None):
    """
    预览数据集中的所有数据文件
    
    Args:
        dataset_path (str): 数据集路径
        output_file (str, optional): 输出文件路径，如果为None则打印到控制台
    """
    # 获取所有数据文件
    data_files = []
    
    for ext in ['*.json', '*.parquet']:
        data_files.extend(Path(dataset_path).rglob(ext))
    
    output_content = []
    output_content.append(f"发现 {len(data_files)} 个数据文件\n")
    
    for file_path in sorted(data_files):
        output_content.append(f"="*80)
        output_content.append(f"文件路径: {file_path}")
        output_content.append(f"="*80)
        
        try:
            if file_path.suffix == '.json':
                # 处理JSON文件
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    # 如果是列表，取前5个元素
                    preview_data = data[:5]
                    output_content.append(f"数据类型: 列表 (共{len(data)}项)")
                    output_content.append(f"前5项内容:")
                    for i, item in enumerate(preview_data):
                        output_content.append(f"  [{i}]: {item}")
                elif isinstance(data, dict):
                    # 如果是字典，打印整个字典（限制大小）
                    output_content.append(f"数据类型: 字典")
                    output_content.append(f"键数量: {len(data)}")
                    output_content.append(f"内容预览: {str(data)[:500]}...")
                    if len(str(data)) > 500:
                        output_content.append("... (内容被截断)")
                else:
                    output_content.append(f"数据类型: {type(data).__name__}")
                    output_content.append(f"内容: {data}")
                    
            elif file_path.suffix == '.parquet':
                # 处理Parquet文件
                df = pd.read_parquet(file_path)
                output_content.append(f"数据类型: DataFrame")
                output_content.append(f"形状: {df.shape[0]} 行 × {df.shape[1]} 列")
                output_content.append(f"列名: {list(df.columns)}")
                
                if len(df) > 0:
                    output_content.append(f"\n前5行数据:")
                    output_content.append(str(df.head()))
                else:
                    output_content.append("数据框为空")
            
            output_content.append("\n")
            
        except Exception as e:
            output_content.append(f"读取文件时出错: {e}\n")
    
    # 根据是否指定了输出文件来决定输出方式
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(output_content))
        print(f"结果已保存到文件: {output_file}")
    else:
        for line in output_content:
            print(line)

if __name__ == "__main__":
    dataset_path = "/Users/watuji/MyGitDev/benchmark/dataset"
    output_file = "/Users/watuji/MyGitDev/benchmark/dataset_preview.txt"  # 默认输出文件
    
    if not os.path.exists(dataset_path):
        print(f"错误: 路径 {dataset_path} 不存在")
    else:
        preview_data_files(dataset_path, output_file)