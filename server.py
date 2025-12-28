from pydoc import describe
from fastmcp import FastMCP
import random
import subprocess, time
from datetime import datetime

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

# ======================================================================

@mcp.tool(
        name="get_moisture_level",
        description="Get the current moisture level"
        )
def get_moisture_level() -> int:
    level = random.randint(0, 100)
    print(f"[MCP] get_moisture_level() -> {level}%")
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

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp", stateless_http=True)
