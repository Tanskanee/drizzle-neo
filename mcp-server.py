from pydoc import describe
from fastmcp import FastMCP
import random
from datetime import datetime
from typing import Annotated

from mcp_scripts import ordinal, get_wttr, rag

mcp = FastMCP("MoistureSensor")

# Intended to simulate readings from a real moisture sensor connected to a potted plant's soil
@mcp.tool(
        name="get_moisture_level",
        description="Get the current moisture level"
        )
def get_moisture_level() -> str:
    level = random.randint(0, 100)
    level = str(level)+"%"
    print(f"[MCP] get_moisture_level() -> {level}")
    return level

@mcp.tool(
        name="get_date_and_time",
        description="Get the current date and time"
)
def get_date_and_time() -> str:
    date = f"{datetime.now().strftime('%A')} {(ordinal(datetime.now().day))} {datetime.now().strftime('%B %Y %H:%M')}"
    print(f"[MCP] get_date_and_time() -> {date}")
    return date

@mcp.tool(
        name="get_weather",
        description="Get weather in current location"
)
def get_weather() -> str:
    weather = get_wttr()
    if weather is None:
        return ""
    weather = weather.replace("°C", " Celsius")
    print(f"[MCP] get_weather() -> {weather}")
    return weather

@mcp.tool(
        name="recall_longterm_memory",
        description="Return relevant snippets from archived conversations based on given keyword or sentence using retrieval-augmented generation (RAG). Use if you yourself need to recall something or if the user requires you to recall something."
)
def recall_longterm_memory(query: str,
                           num_snippets: Annotated[int, "The more snippets, the wider the scope of the search. min=5, max=15"] = 5,
                           window_size: Annotated[int, "The amount of surrounding messages included around a retrieved snippet. min=2, max=5"] = 2
                          ) -> str:
    if num_snippets > 15:
        num_snippets = 15
    if window_size > 5:
        window_size = 5
    retrieved = "========== SNIPPETS FROM PREVIOUS CONVERSATIONS ==========\n"
    retrieved = retrieved + rag(query,num_snippets,window_size) + "\n"
    retrieved = retrieved + "========== END CONVERSATION SNIPPETS =========="
    print(f"[MCP] recall_longterm_memory({query},{num_snippets},{window_size}) -> {retrieved}")
    return retrieved

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp", stateless_http=True)
