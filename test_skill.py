#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import skills

# 加载内置技能
skills.load_builtin_skills()

# 获取所有技能
from skills import get_skills
skills_list = get_skills()

print(f"找到技能数量: {len(skills_list)}")
print("\n技能列表:")
for skill in skills_list:
    print(f"- {skill['id']}: {skill['name']} ({skill['icon']})")

# 检查剧本生成技能
script_skill = None
for skill in skills_list:
    if skill['id'] == 'script_generator':
        script_skill = skill
        break

if script_skill:
    print("\n✅ 剧本生成技能验证成功:")
    print(f"  技能ID: {script_skill['id']}")
    print(f"  技能名称: {script_skill['name']}")
    print(f"  技能描述: {script_skill['description']}")
    print(f"  技能图标: {script_skill['icon']}")
    print(f"  触发词: {script_skill['triggers']}")
    print(f"  示例: {script_skill['examples']}")
else:
    print("\n❌ 剧本生成技能未找到!")
