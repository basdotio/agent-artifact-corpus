from fastmcp import FastMCP
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

mcp = FastMCP("Data Visualization Server")


@mcp.tool
def generate_plot(file_path: str, chart_type: str,  x: str = None, y: str = None):
    """
    Generates a simple chart (bar, scatter, histogram) using given columns.
    Returns path to saved chart image.
    """
    # Load data
    df = pd.read_csv(file_path)

    # Create plot based on chart type
    fig, ax = plt.subplots(figsize=(6, 4))
    if chart_type == "bar":
        sns.barplot(data=df, x=x, y=y, ax=ax)
    elif chart_type == "scatter":
        sns.scatterplot(data=df, x=x, y=y, ax=ax)
    elif chart_type == "histogram":
        sns.histplot(data=df, x=x, bins=20, kde=True, ax=ax)
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")

    # Save plot to file
    plt.tight_layout()
    chart_path = f"chart_{chart_type}.png"
    plt.savefig(chart_path)
    plt.close(fig)

    return {"chart_path": os.path.abspath(chart_path)}


if __name__ == "__main__":
    mcp.run()