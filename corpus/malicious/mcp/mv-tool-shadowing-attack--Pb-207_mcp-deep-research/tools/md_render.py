import re
from flask import Flask, request, render_template_string

app = Flask(__name__)

class MarkdownRenderer:
    def __init__(self):
        # 存储各种标记的正则表达式模式
        self.patterns = {
            'header': re.compile(r'^(#{1,6})\s(.+)$', re.MULTILINE),
            'bold': re.compile(r'\*\*(.+?)\*\*'),
            'italic': re.compile(r'\*(.+?)\*'),
            'link': re.compile(r'\[([^\]]+)\]\(([^)]+)\)'),
            'image': re.compile(r'!\[([^\]]+)\]\(([^)]+)\)'),
            'code': re.compile(r'`([^`]+)`'),
            'blockquote': re.compile(r'^>\s(.+)$', re.MULTILINE),
            'hr': re.compile(r'^-{3,}$', re.MULTILINE),
            'ul': re.compile(r'^[\*\-\+]\s(.+)$', re.MULTILINE),
            'ol': re.compile(r'^\d+\.\s(.+)$', re.MULTILINE)
        }

    def render(self, markdown_text: str) -> str:
        if not markdown_text.strip():
            return ""

        # 处理换行
        html = markdown_text.replace('\n\n', '</p><p>')
        html = f"<p>{html}</p>"

        # 按优先级顺序处理各种标记
        html = self._process_headers(html)
        html = self._process_horizontal_rule(html)
        html = self._process_images(html)
        html = self._process_links(html)
        html = self._process_bold(html)
        html = self._process_italic(html)
        html = self._process_code(html)
        html = self._process_lists(html)
        html = self._process_blockquotes(html)

        # 清理空的段落标记
        html = html.replace('<p></p>', '')
        return html

    def _process_headers(self, text: str) -> str:
        def replace_header(match):
            level = len(match.group(1))
            content = match.group(2)
            return f"<h{level}>{content}</h{level}>"

        return self.patterns['header'].sub(replace_header, text)

    def _process_bold(self, text: str) -> str:
        return self.patterns['bold'].sub(r'<strong>\1</strong>', text)

    def _process_italic(self, text: str) -> str:
        return self.patterns['italic'].sub(r'<em>\1</em>', text)

    def _process_links(self, text: str) -> str:
        return self.patterns['link'].sub(r'<a href="\2">\1</a>', text)

    def _process_images(self, text: str) -> str:
        return self.patterns['image'].sub(r'<img src="\2" alt="\1">', text)

    def _process_code(self, text: str) -> str:
        return self.patterns['code'].sub(r'<code>\1</code>', text)

    def _process_blockquotes(self, text: str) -> str:
        return self.patterns['blockquote'].sub(r'<blockquote>\1</blockquote>', text)

    def _process_horizontal_rule(self, text: str) -> str:
        return self.patterns['hr'].sub('<hr>', text)

    def _process_lists(self, text: str) -> str:
        # 无序列表处理
        text = self.patterns['ul'].sub(r'<li>\1</li>', text)
        # 有序列表处理
        text = self.patterns['ol'].sub(r'<li>\1</li>', text)

        # 将连续列表项分组为ul或ol
        lines = text.split('</p><p>')
        in_list = False
        for i, line in enumerate(lines):
            if '<li>' in line and not in_list:
                in_list = True
                lines[i] = f"<ul>{line}"
            elif '<li>' not in line and in_list:
                in_list = False
                lines[i-1] = f"{lines[i-1]}</ul>"
        text = '</p><p>'.join(lines)
        return text

# 创建全局渲染器实例
renderer = MarkdownRenderer()

# HTML模板
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Markdown 渲染器</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
        }
        .container {
            display: flex;
            gap: 20px;
        }
        .editor, .preview {
            flex: 1;
        }
        textarea {
            width: 100%;
            height: 500px;
            padding: 10px;
            font-family: monospace;
        }
        .preview {
            border: 1px solid #ddd;
            padding: 10px;
            overflow-y: auto;
            height: 522px;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        code {
            background-color: #f0f0f0;
            padding: 2px 4px;
            border-radius: 3px;
        }
        pre code {
            display: block;
            background-color: #f8f8f8;
            padding: 10px;
            overflow-x: auto;
        }
    </style>
</head>
<body>
    <h1>Markdown 实时预览</h1>
    <div class="container">
        <div class="editor">
            <h3>编辑 Markdown</h3>
            <form method="POST">
                <textarea name="markdown" placeholder="在这里输入Markdown内容...">{{ markdown_text }}</textarea>
                <button type="submit">渲染查看</button>
            </form>
        </div>
        <div class="preview">
            <h3>预览</h3>
            {% if rendered_html %}
                {{ rendered_html|safe }}
            {% else %}
                <p>渲染后的HTML将出现在这里...</p>
            {% endif %}
        </div>
    </div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    markdown_text = ""
    rendered_html = ""

    if request.method == "POST":
        markdown_text = request.form.get("markdown", "")
        if markdown_text.strip():
            rendered_html = renderer.render(markdown_text)

    return render_template_string(HTML_TEMPLATE,
                                markdown_text=markdown_text,
                                rendered_html=rendered_html)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=3456, debug=True)