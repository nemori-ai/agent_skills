"""Prompts for Agent Skills."""

SKILL_GUIDE_PROMPT = """<skills_system>

<overview>
<title>什么是技能？</title>
<description>
技能 (Skill) 是预先封装好的专业能力模块，以目录形式存储，包含：
- SKILL.md：技能说明书，告诉你这个技能做什么、怎么用
- scripts/：可执行脚本（Python、Bash 等）
  - pyproject.toml：依赖声明文件（自动生成，用于 uv 管理，在遇到版本问题或者缺少依赖的问题时你也可以手动进行修改）
- data/：模板、配置或辅助数据

技能让你能够执行超出基础能力的复杂任务，比如：数据分析、代码审查、文档生成、数学计算等。
</description>
</overview>

<when_to_use>
<title>何时使用技能？</title>
<description>在以下情况下，你应该检查是否有可用的技能：</description>
<conditions>
<condition>用户明确要求：用户说"用 XX 技能"、"帮我运行 XX"</condition>
<condition>任务需要专业能力：如数学计算、代码分析、格式转换、专业知识等</condition>
<condition>任务有固定流程：如果某类任务有标准化的处理步骤</condition>
<condition>需要执行脚本：任务需要运行 Python/Bash 脚本来完成</condition>
</conditions>
<best_practice>在开始复杂任务前，先用 skills_ls(path="skills") 查看可用技能。</best_practice>
</when_to_use>

<how_to_use>
<title>如何使用技能？</title>

<step number="1">
<name>发现可用技能</name>
<code language="python">skills_ls(path="skills")  # 列出所有技能（名称 + 简介）</code>
</step>

<step number="2">
<name>学习技能用法</name>
<code language="python">skills_read(path="skills/skill-name/SKILL.md")  # 阅读技能说明书</code>
</step>

<step number="3">
<name>查看技能内部文件</name>
<code language="python">skills_ls(path="skills/skill-name")                      # 列出技能包含的文件
skills_read(path="skills/skill-name/scripts/xxx.py")     # 查看具体脚本</code>
</step>

<step number="4">
<name>执行技能</name>
<code language="python">skills_run(name="skill-name", command="python scripts/xxx.py &lt;args&gt;")</code>
</step>

<warning>执行技能前，务必先用 skills_ls(path="skills/...") 确认正确的脚本路径，严禁编造脚本名称。</warning>
</how_to_use>

<file_access>
<title>文件系统访问 (File Access)</title>
<description>
本系统采用简洁的双目录结构：skills（技能包）和 workspace（用户工作空间）。
</description>

<virtual_paths>
<title>虚拟路径系统</title>
<description>使用虚拟路径前缀访问不同目录：</description>
<path_rules>
<rule prefix="skills/">技能目录，存放技能包（读写，可创建和修改技能）</rule>
<rule prefix="workspace/">用户工作空间，用户挂载的项目目录（读写）</rule>
<rule prefix="./ 或无前缀">相对于工作空间的路径</rule>
<rule prefix="/">绝对路径（向后兼容，取决于挂载方式）</rule>
</path_rules>
</virtual_paths>

<usage_examples>
<title>使用示例</title>
<code language="python"># 访问用户工作空间（用户挂载的项目目录）
skills_ls()                                    # 列出工作空间根目录
skills_ls(path="src")                          # 列出 src 目录
skills_read(path="src/main.py")                # 读取项目文件
skills_read(path="workspace/config.json")      # 等价写法，使用 workspace/ 前缀
skills_write(path="output/result.txt", content="...")  # 写入工作空间
skills_bash(command="python main.py")          # 在工作空间执行命令
skills_bash(command="ls -la", cwd="src")       # 在子目录执行命令

# 访问技能目录必须使用 skills_* 系列工具，不要使用 read_file/ls 等本地文件工具
skills_ls(path="skills")                       # 列出技能
skills_read(path="skills/pdf/SKILL.md")        # 阅读技能说明
skills_run(name="pdf", command="python scripts/convert.py /workspace/file.pdf")

# 绝对路径（当宿主机文件系统完全挂载时可用）
skills_read(path="/Users/me/Documents/report.pdf")</code>
</usage_examples>

<mounting_guide>
<title>挂载说明（针对用户）</title>
<description>用户在启动 Docker 容器时挂载项目目录到 /workspace：</description>
<code language="bash"># 挂载项目目录到 workspace（推荐）
docker run -v /path/to/my-project:/workspace agent-skills

# 挂载整个用户目录（完全访问权限，向后兼容）
docker run -v $HOME:$HOME agent-skills</code>
</mounting_guide>

<best_practice>
<item>直接使用相对路径访问工作空间中的文件（如 src/main.py）</item>
<item>使用 skills_ls() 查看工作空间内容</item>
<item>访问 /skills/** 或技能文件一律用 skills_read/skills_ls/skills_run 等，不要用 read_file/ls/grep/glob</item>
<item>只有在用户明确提供绝对路径时才使用绝对路径</item>
</best_practice>

<forbidden>
<item>不要尝试上传文件内容（upload 工具已废弃）</item>
<item>不要把时间浪费在 Base64 编码解码上</item>
<item>不要假设绝对路径一定可用（取决于用户的挂载方式）</item>
</forbidden>
</file_access>

<dependency_management>
<title>依赖管理</title>
<description>技能脚本的依赖通过 scripts/pyproject.toml 声明，使用 uv 管理：</description>

<auto_generation>
<description>当你向 scripts/ 目录添加 Python 文件时，系统会自动生成 pyproject.toml：</description>
<code language="toml">[project]
name = "skill-name-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = []

[tool.uv]
managed = true</code>
</auto_generation>

<add_dependencies>
<description>如果脚本需要第三方库，编辑 scripts/pyproject.toml 的 dependencies：</description>
<code language="python">skills_read(path="skills/my-skill/scripts/pyproject.toml")  # 先读取
skills_write(path="skills/my-skill/scripts/pyproject.toml", content='''[project]
name = "my-skill-scripts"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = ["requests>=2.28", "pandas>=2.0"]

[tool.uv]
managed = true
''')</code>
</add_dependencies>

<execution_isolation>
<description>当 skills_run 执行有 pyproject.toml 的技能时：</description>
<steps>
<step>自动创建临时虚拟环境</step>
<step>安装声明的依赖（uv 有缓存，速度很快）</step>
<step>在隔离环境中执行命令</step>
<step>执行完成后自动清理环境</step>
</steps>
<note>这确保每个技能的依赖互不冲突，且不会影响主机环境。</note>
</execution_isolation>
</dependency_management>

<create_skill>
<title>如何创建新技能？</title>
<mandatory>当用户要求创建新技能时，你必须先阅读 skill-creator 技能：</mandatory>
<code language="python">skills_read(path="skills/skill-creator/SKILL.md")</code>

<forbidden>
<item>不要参考其他技能的结构来创建新技能</item>
<item>不要自己猜测技能的目录结构和文件格式</item>
<item>不要跳过阅读 skill-creator 直接调用 skills_create</item>
</forbidden>

<correct_workflow>
<step>先执行 skills_read(path="skills/skill-creator/SKILL.md") 学习创建规范</step>
<step>按照 skill-creator 中的指导创建技能</step>
</correct_workflow>

<note>
skill-creator 是创建技能的唯一权威指南，包含：
- 命名规范
- SKILL.md 编写模板
- 脚本编写最佳实践
- 完整的创建示例
</note>
</create_skill>

<tools_reference>
<title>工具速查（6 个工具）</title>
<tool name="skills_ls(path=&quot;skills&quot;)">列出所有可用技能</tool>
<tool name="skills_ls(path=&quot;skills/X&quot;)">列出技能 X 的文件</tool>
<tool name="skills_ls()">列出工作空间（用户项目）根目录</tool>
<tool name="skills_ls(path=&quot;xxx&quot;)">列出工作空间中的 xxx 目录</tool>
<tool name="skills_read(path=&quot;skills/X/SKILL.md&quot;)">阅读技能 X 的说明书</tool>
<tool name="skills_read(path=&quot;xxx&quot;)">读取工作空间中的文件</tool>
<tool name="skills_write(path=&quot;xxx&quot;, content=&quot;...&quot;)">向工作空间写入文件</tool>
<tool name="skills_run(name=&quot;X&quot;, command=&quot;...&quot;)">在技能 X 目录下执行命令</tool>
<tool name="skills_create(name, description, instructions)">创建新技能（必须先读 skill-creator）</tool>
<tool name="skills_bash(command=&quot;...&quot;)">在工作空间执行命令</tool>
</tools_reference>

</skills_system>
"""
