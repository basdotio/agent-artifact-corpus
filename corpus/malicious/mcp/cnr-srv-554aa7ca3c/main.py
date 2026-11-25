# ---------------- Init Logic ----------------
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Sentiment Analysis Tool")


@mcp.tool()
def sentiment_analysis(text: str) -> str:
    """Analyze sentiment of text and return 'positive', 'neutral', or 'negative'."""
    positive_words = {"good", "great", "happy", "love"}
    negative_words = {"bad", "sad", "angry", "hate"}
    score = 0
    for word in text.lower().split():
        if word in positive_words:
            score += 1
        elif word in negative_words:
            score -= 1
    if score > 0:
        return "positive"
    elif score < 0:
        return "negative"
    else:
        return "neutral"


if __name__ == "__main__":
    mcp.run()
