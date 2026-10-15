# -*- coding: utf-8 -*-
"""
init_config.py
大学通用实验报告 - 学生身份配置向导 (Student Profile Config Wizard)
主动向用户询问个人学籍信息，并在本地安全保存为 .labreport_config.json。
该文件已被 .gitignore 保护，绝不会被上传或泄露，后续生成报告时可直接自动读取！
"""

import os
import sys
import json

CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".labreport_config.json")

def prompt_input(field_name, default_val=""):
    prompt = f"👉 请输入【{field_name}】"
    if default_val:
        prompt += f" [默认: {default_val}]: "
    else:
        prompt += ": "
    
    val = input(prompt).strip()
    if not val:
        return default_val
    return val

def main():
    print("=" * 60)
    print(" 🎓 大学通用实验报告 Skill - 个人学籍信息配置向导")
    print("=" * 60)
    print("本向导将帮助你设置生成实验报告所需的表头信息。")
    print("信息仅保存在你本地电脑的 .labreport_config.json 中，绝不上传到任何服务器或 Git 仓库。\n")

    current_config = {}
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                current_config = json.load(f)
            print("💡 检测到已有本地配置，直接按 Enter 键可保留原有内容。\n")
        except Exception:
            pass

    university = prompt_input("学校名称", current_config.get("university", "四川轻化工大学"))
    department = prompt_input("所属学院", current_config.get("department", "计算机科学与工程学院"))
    major = prompt_input("所在专业", current_config.get("major", "网络工程"))
    class_num = prompt_input("行政班号", current_config.get("class_num", "20241"))
    name = prompt_input("学生姓名", current_config.get("name", ""))
    student_id = prompt_input("学生学号", current_config.get("student_id", ""))
    lab_name = prompt_input("实验室名称", current_config.get("lab_name", "专业教学实验室"))

    config_data = {
        "university": university,
        "department": department,
        "major": major,
        "class_num": class_num,
        "name": name,
        "student_id": student_id,
        "lab_name": lab_name,
        "group_num": "01",
        "date": "2026年秋季"
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 60)
    print(f"✅ 配置已成功保存至: {CONFIG_PATH}")
    print("在生成实验报告时，系统将自动加载此配置，无需重复输入！")
    print("若需要修改，随时再次运行本脚本即可。")
    print("=" * 60)

if __name__ == "__main__":
    main()
