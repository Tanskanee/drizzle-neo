FROM python:3.14-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git libasound2-dev

WORKDIR /app

VOLUME /app/state
VOLUME /app

COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.lock

# Copy required application code
COPY app.py assistant.py audio.py config.json mcp-server.py prompt.py ./

# Expose the Flask server port (5000)
EXPOSE 5000

# Start MCP server and Flask app
CMD ["sh", "-c", "python mcp-server.py & python app.py"]
