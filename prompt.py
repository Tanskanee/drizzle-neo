import requests
import argparse
import json
import os
import re
import subprocess
from openai import OpenAI

def load_config():
    with open('config.json') as f:
        cfg = json.load(f)
    global server_url, mcp_url, model, prompt1, prompt2, prompt3, memory_model, memory_prompt, memory_maxlines, memory
    server_url = cfg['server']['url']
    mcp_url = cfg['mcp']['url']

    model = cfg['model']['model']
    prompt1 = cfg['model']['prompt1']
    prompt2 = cfg['model']['prompt2']
    prompt3 = cfg['model']['prompt3']

    memory_model = cfg['memory']['model']
    memory_prompt = cfg['memory']['prompt']
    memory_maxlines = cfg['memory']['max_lines']

    with open('./state/memory.txt', 'r') as f:
        memory = f.read()

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--prompt", required=True, help="Prompt to send to the LLM")
    parser.add_argument("-d","--debug", action='store_true', help="Print various debug information, such as the LLM's full reply")
    parser.add_argument("-notts","--no-tts", action='store_true', help="Disable text-to-speech")
    args = parser.parse_args()
    return args

def get_tools():
    url = mcp_url
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    payload = {
        "jsonrpc": "2.0",
        "id": 4,
        "method": "tools/list",
        "params": {}
    }
    resp = requests.post(url, headers=headers, json=payload)

    if resp.headers.get("Content-Type", "").startswith("application/json"):
        data = resp.json()
    else:
        data_line = None
        for line in resp.text.splitlines():
            line = line.strip()
            if line.startswith("data:"):
                data_line = line[len("data:"):].strip()
                break
        if data_line is None:
            raise RuntimeError("No data field in SSE response from MCP")
        data = json.loads(data_line)

    tool_list = data.get("result", {}).get("tools", [])
    openai_tools = []
    for t in tool_list:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t.get("description", ""),
                "parameters": t.get("inputSchema", {"type": "object"})
            }
        })
    return openai_tools

def prompt_llm(prompt,debug):
    tools = get_tools()
    tool_names = ", ".join([t["function"]["name"] for t in tools])
    if debug:
        print("--- Tool Definitions ---")
        print(tools)
        print()
        print("--- Tools ---")
        print(tool_names)
        print()

    apikey = os.getenv("OPENAI_API_KEY"),
    if apikey is None:
        apikey = ""

    client = OpenAI(
        base_url = server_url,
        api_key = str(apikey),
    )
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt1+prompt2+prompt3 + "Your memory: " + memory + "You have access to the following tools: " + tool_names},
            {"role": "user", "content": prompt},
        ],
        tools=tools,
        tool_choice="auto"
    )

    message = completion.choices[0].message

    # Check if the model decided to call a tool
    # These two lines below are full of LSP errors but work fine, just ignore
    if getattr(message, "tool_calls", None) and len(message.tool_calls) > 0:
        tool_name = message.tool_calls[0].function.name
        if debug:
            print("--- Selected Tool ---")
            print(tool_name)
            print()
    
    if debug:
        print("--- Full Message ---")
        return message
    else:
        return message.content

def tts(reply):
    reply_sanitized = reply.replace("’", "'")
    reply_sanitized = reply_sanitized.replace("*", "")
    reply_sanitized = reply_sanitized.replace("…", "...")
    reply_sanitized = reply_sanitized.replace("—", "- ")
    reply_sanitized = re.sub(r"\(.*?\)", "", reply_sanitized)   # Remove "roleplay" text (text inside parenthesis)
    reply_sanitized = reply_sanitized.encode('ascii', 'ignore').decode('utf-8') # Remove all emojis
    reply_sanitized = reply_sanitized.lower()   # turn all uppercase letters to lowercase

    subprocess.run(['python3', 'audio.py', reply_sanitized])

def main():
    load_config()
    args = parse_args()
    reply = prompt_llm(args.prompt,args.debug)
    print(reply)
    if not args.no_tts:
        tts(reply)

if __name__ == "__main__":
    main()
