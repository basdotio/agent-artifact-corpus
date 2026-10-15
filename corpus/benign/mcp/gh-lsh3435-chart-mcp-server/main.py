from fastmcp import FastMCP
import matplotlib.pyplot as plt
import io
import base64
from PIL import Image

# 初始化MCP服务
mcp = FastMCP("chart-server")

# ----------------------工具1：24小时温湿度双轴图----------------------
@mcp.tool()
def genDualAxisChart(categories: list[str], temp_data: list[int], humidity_data: list[int], chart_title: str, x_title: str) -> str:
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax1 = plt.subplots(figsize=(10, 5))

    color1 = "#ff6b6b"
    ax1.set_xlabel(x_title)
    ax1.set_ylabel("气温(℃)", color=color1)
    ax1.plot(categories, temp_data, color=color1, marker="o", label="气温")
    ax1.tick_params(axis="y", labelcolor=color1)

    ax2 = ax1.twinx()
    color2 = "#4ecdc4"
    ax2.set_ylabel("相对湿度(%)", color=color2)
    ax2.plot(categories, humidity_data, color=color2, marker="s", label="湿度")
    ax2.tick_params(axis="y", labelcolor=color2)

    plt.title(chart_title)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    # 返回图片base64，敏学平台可直接渲染
    return f"data:image/png;base64,{img_base64}"

# ----------------------工具2：15天逐日气温折线图----------------------
@mcp.tool()
def gen15DayLineChart(date_list: list[str], day_temp: list[int], night_temp: list[int], chart_title: str) -> str:
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(12,5))
    ax.plot(date_list, day_temp, marker="o", color="#ff7875", label="白天温度")
    ax.plot(date_list, night_temp, marker="^", color="#5cdbd3", label="夜间温度")
    ax.set_title(chart_title)
    ax.legend()
    plt.xticks(rotation=30)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return f"data:image/png;base64,{img_base64}"

# ----------------------工具3：AQI空气质量柱状图----------------------
@mcp.tool()
def genAqiBarChart(data: list[dict], chart_title: str) -> str:
    plt.rcParams["font.sans-serif"] = ["WenQuanYi Zen Hei"]
    plt.rcParams["axes.unicode_minus"] = False
    categories = [item["category"] for item in data]
    values = [item["value"] for item in data]
    fig, ax = plt.subplots(figsize=(10,5))
    bars = ax.bar(categories, values, color="#4096ff")
    ax.set_title(chart_title)
    ax.bar_label(bars)
    fig.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight", dpi=150)
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
    plt.close()
    return f"data:image/png;base64" + "," + img_base64

# 启动MCP HTTP服务，streamableHttp模式
if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=10000)
