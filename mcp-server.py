from pydoc import describe
from fastmcp import FastMCP
import random
import subprocess, time
from datetime import datetime
import json
from pathlib import Path
from typing import Annotated
from sentence_transformers import SentenceTransformer, util

mcp = FastMCP("MoistureSensor")

# ======================================================================

# Function to get time and date in correct format
def _ordinal(day: int) -> str:
   if 10 <= (day % 100) <= 20:
       suffix = "th"
   else:
       suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
   return f"{day}{suffix}"

# Get the current temperature and precipitation using the wttr.in service using curl
fmt = "Location:%20%l%0ATemperature:%20%t%0APrecipitation:%20%p"
url = f"https://wttr.in/?format={fmt}"
def get_wttr(retries: int=1, delay: float=1.0):
    for attempt in range(retries + 1):
        result = subprocess.run(
            ["curl", "-s", url], capture_output=True, text=True
        )
        if result.returncode == 0:                     # success
            return result.stdout.strip()
        if result.returncode == 52 and attempt < retries:
            # curl "empty reply"; retry after a short pause
            time.sleep(delay)
            continue
        # any other error (or final 52 attempt)
        return f"curl error {result.returncode}"

# Retrieve relevant archived conversation snippets
def rag(prompt,num_snippets,window_size):
    embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

    archive_path = Path("./state/context-archive.json")
    if not archive_path.is_file():                     # file missing
        archive_path.parent.mkdir(parents=True, exist_ok=True)  # ensure ./state exists
        archive_path.write_text(
            json.dumps({"history": []}, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    top_k = num_snippets
    window = window_size

    # load archive
    with open(archive_path, encoding="utf-8") as f:
        data = json.load(f)
    history = data.get("history", [])
    if not history:
        return ""

    # make sure every entry has a string for content
    for msg in history:
        if msg.get("content") is None:
            msg["content"] = ""

    # encode the query and all messages
    q_emb = embedding_model.encode([prompt], normalize_embeddings=True)
    c_emb = embedding_model.encode([msg["content"] for msg in history], normalize_embeddings=True)

    # cosine similarity -> top‑k indices & scores (descending order)
    scores = util.cos_sim(q_emb, c_emb).flatten()
    top_vals, top_idxs = scores.topk(k=min(top_k, len(history)), largest=True)

    # build a labelled block for each hit
    blocks = [] # will hold (rank, block_string)

    for rank, (score, idx) in enumerate(zip(top_vals.tolist(), top_idxs.tolist()), start=1):
        # window around the hit
        start = max(0, idx - window)
        end   = min(len(history), idx + window + 1)

        # header
        header = f"===== Snippet Relevancy: {rank} (score: {score:.3f}) ====="

        # body (role + content)
        body = "\n".join(
            f"{history[i]['role']}: {history[i]['content']}"
            for i in range(start, end)
        )

        blocks.append((rank, f"{header}\n{body}"))

    # reverse order (top-to-bottom = low_score -> high_score)
    ordered_strings = [block for _, block in reversed(blocks)]

    return "\n\n".join(ordered_strings)

# ======================================================================

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
    date = f"{datetime.now().strftime('%A')} {(_ordinal(datetime.now().day))} {datetime.now().strftime('%B %Y %H:%M')}"
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
