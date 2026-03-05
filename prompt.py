import requests
from pathlib import Path
import argparse
import json
import os
import re
import subprocess
from sentence_transformers import SentenceTransformer
from openai import OpenAI

# Global variable to hold the chosen context file name (default: context.json)
context_file_path = "context.json"

# load configuration options and make them global variables
def load_config():
    with open('config.json') as f:
        cfg = json.load(f)
    global server_url, mcp_url, model, prompt1, prompt2, prompt3, memory_model, memory_prompt, memory_maxmsgs, memory
    server_url = cfg['server']['url']
    mcp_url = cfg['mcp']['url']

    model = cfg['model']['model']
    prompt1 = cfg['model']['prompt1']
    prompt2 = cfg['model']['prompt2']
    prompt3 = cfg['model']['prompt3']

    memory_model = cfg['memory']['model']
    memory_prompt = cfg['memory']['prompt']
    memory_maxmsgs = cfg['memory']['max_messages']

    # create state/memory.txt if it doesn't exist yet and load it
    memory_path = Path("./state/memory.txt")
    if not memory_path.is_file():
        memory_path.parent.mkdir(parents=True, exist_ok=True)
        memory_path.write_text("")
    with open(memory_path, 'r') as f:
        memory = f.read()

# create state/context file if it doesn't exist yet and load it
def load_context():
    context_path = Path(f"./state/{context_file_path}")
    if not context_path.is_file():
        context_path.parent.mkdir(parents=True, exist_ok=True)
        context_path.write_text(json.dumps({"version": 1, "history": []}, ensure_ascii=False, indent=2))
        return {"version": 1, "history": []}
    with open(context_path, "r+", encoding="utf-8") as f:
        context = json.load(f)
    return(context)

# append user's prompt and LLM's response to context file
def save_context(prompt,reply,context_entries=None):
    context_path = Path(f"./state/{context_file_path}")

    context_path.parent.mkdir(parents=True, exist_ok=True)
    if not context_path.exists():
        context_path.write_text(json.dumps({"version": 1, "history": []}, ensure_ascii=False, indent=2))

    with context_path.open("r+", encoding="utf-8") as f:
        context = json.load(f)
        context["history"].append({"role": "user", "content": prompt})
        
        if context_entries:
            for entry in context_entries:
                context["history"].append(entry)
        else:
            context["history"].append({"role": "assistant", "content": reply})
        
        f.seek(0)
        json.dump(context, f, ensure_ascii=False, indent=2)
        f.truncate()

# command line arguments, run `$ python prompt.py -h` to view them
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--prompt", required=True, help="Prompt to send to the LLM")
    parser.add_argument("-d","--debug", action='store_true', help="Print various debug information, such as the LLM's full reply")
    parser.add_argument("-notts","--no-tts", action='store_true', help="Disable text-to-speech")
    parser.add_argument("-ns","--no-save", action='store_true', help="Disable saving messages to context.json")
    parser.add_argument("-cf", "--contextfile", default="context.json",
                        help="Context JSON file to use for saving and loading conversation history")
    args = parser.parse_args()
    return args

# get tool names from the MCP server
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

# call a tool the LLM wants to call and return what the MCP server outputs
def call_tool(tool_name,tool_args):
    url = mcp_url

    if isinstance(tool_args, str):
        tool_args = json.loads(tool_args)

    payload = {
      "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
          "name": tool_name,
          "arguments": tool_args
        },
    }
    headers = { 
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json"
    }
    r = requests.post(url, json=payload, headers=headers, stream=True)
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if line.startswith("data:"):
            json_str = line.split(":", 1)[1].strip()
            if json_str:
                try:
                    data = json.loads(json_str)
                except json.JSONDecodeError:
                    continue
                result = data.get("result")
                if result:
                    if isinstance(result, dict) and "structuredContent" in result and "result" in result["structuredContent"]:
                        return result["structuredContent"]["result"]
                    return result
                if "error" in data:
                    raise RuntimeError(f"Tool error: {data['error']}")
    raise RuntimeError("No valid result found in response")

def assemble_payload(prompt,debug):
    # Load tool information
    tools = get_tools()
    tool_names = ", ".join([t["function"]["name"] for t in tools])
    if debug:
        print("--- Tool Definitions ---")
        print(tools)
        print()
        print("--- Available Tools ---")
        print(tool_names)
        print()

    # construct system prompt
    system_prompt = (
        prompt1
        + "\n\n"
        + prompt2
        + "\n\n"
        + prompt3
        + "\n\n"
        + "Your memory:"
        + "\n"
        + memory
        + "\n\n"
        + "You have access to the following tools:"
        + "\n"
        + tool_names
    )

    if debug:
        print("--- Full System Prompt ---")
        print(system_prompt)
        print("--------------------------")
        print()

    # load context + append user prompt to it
    context = load_context()
    context["history"].append({"role": "user", "content": prompt})

    # create payload and append system prompt as the first value 
    payload = []
    payload.append({"role": "system", "content": system_prompt})

    # add context to payload
    for entry in context["history"]:
        payload_entry = {"role": entry["role"]}
        
        if "content" in entry:
            payload_entry["content"] = entry["content"]
        
        if "tool_calls" in entry:
            payload_entry["tool_calls"] = entry["tool_calls"]
        
        if "tool_call_id" in entry:
            payload_entry["tool_call_id"] = entry["tool_call_id"]
        
        payload.append(payload_entry)

    return (payload,tools)

def prompt_llm(prompt,debug):
    payload,tools = assemble_payload(prompt,debug)

    apikey = os.getenv("OPENAI_API_KEY")
    if apikey is None:
        apikey = ""

    client = OpenAI(
        base_url = server_url,
        api_key = str(apikey),
    )
    completion = client.chat.completions.create(
        model=model,
        messages=payload,
        tools=tools,
        tool_choice="auto"
    )

    message = completion.choices[0].message
    if debug:
        print("--- Full Message Before Tool Call Check ---")
        print(message)

    tool_context_entries = []
    
    # Loop to handle multiple sequential tool calls
    while getattr(message, "tool_calls", None) and len(message.tool_calls) > 0:
        # Process all tool calls in this message
        for tool_call in message.tool_calls:
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments
            tool_call_id = tool_call.id
            if debug:
                print("--- Selected Tool ---")
                print(tool_name)
                if tool_args:
                    print(tool_args)
                print()

            tool_result = call_tool(tool_name,tool_args)
            if debug:
                print("--- Tool Result ---")
                print(tool_result)
                print()

            # Build a new payload that includes the tool call and its result
            # Record the assistant's tool call
            tool_call_entry = {
                "role": "assistant",
                "tool_calls": [
                    {
                        "id": tool_call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": tool_args
                        }
                    }
                ]
            }
            payload.append(tool_call_entry)
            tool_context_entries.append(tool_call_entry)
            
            # Record the tool's response
            tool_response_entry = {
                "role": "tool",
                "content": str(tool_result),
                "tool_call_id": tool_call_id
            }
            payload.append(tool_response_entry)
            tool_context_entries.append(tool_response_entry)
            
            # Save to context file immediately so LLM can see it in next iteration
            context_path = Path(f"./state/{context_file_path}")
            with context_path.open("r+", encoding="utf-8") as f:
                context = json.load(f)
                context["history"].append(tool_call_entry)
                context["history"].append(tool_response_entry)
                f.seek(0)
                json.dump(context, f, ensure_ascii=False, indent=2)
                f.truncate()

        # Get the next response - the LLM may call another tool or provide a final answer
        final_response = client.chat.completions.create(
            model=model,
            messages=payload,
            tools=tools,
            tool_choice="auto",
        )
        message = final_response.choices[0].message
    
    if debug:
        print("--- Full Message ---")
        return message, tool_context_entries
    else:
        return message.content, tool_context_entries

def update_memory_if_required():
    context = load_context()
    n_lines = int(memory_maxmsgs / 2)

    if len(context.get("history", [])) > memory_maxmsgs:
        print(f"--- Context exceeds maximum length ({len(context.get('history', []))}/{memory_maxmsgs})! Pruning and updating context to {n_lines} messages, this may take a while... ---")

        # Construct full memory prompt
        memprompt = memory_prompt
        memprompt += "\n"
        memprompt += "\nThe conversation: " + "\n" + str(context)
        memprompt += "\n"
        memprompt += "\nThe current memory file: " + "\n" + memory

        apikey = os.getenv("OPENAI_API_KEY")
        if apikey is None:
            apikey = ""

        client = OpenAI(
            base_url = server_url,
            api_key = str(apikey),
        )
        completion = client.chat.completions.create(
            model=memory_model,
            messages=[
                {"role": "system", "content": memprompt}
            ]
        )

        # Write newly generated memory to memory.txt
        message = completion.choices[0].message
        #print(message.content)
        Path("./state/memory.txt").write_text(str(message.content))

        # archive deleted messages
        to_remove = context["history"][:-n_lines]
        hist_path = Path("./state/context-archive.json")
        hist_path.parent.mkdir(parents=True, exist_ok=True)
        if hist_path.is_file():
            with hist_path.open("r+", encoding="utf-8") as f:
                try:
                    existing = json.load(f)
                except json.JSONDecodeError:
                    existing = {"history": []}
                existing["history"].extend(to_remove)
                f.seek(0)
                json.dump(existing, f, ensure_ascii=False, indent=2)
                f.truncate()
        else:
            with hist_path.open("w", encoding="utf-8") as f:
                json.dump({"history": to_remove}, f, ensure_ascii=False, indent=2)

        # Trim context.txt
        context["history"] = context["history"][-n_lines:]
        context_path = Path(f"./state/{context_file_path}")
        context_path.parent.mkdir(parents=True, exist_ok=True)
        with context_path.open("r+", encoding="utf-8") as f:
            current = json.load(f)
            current["history"] = context["history"]
            f.seek(0)
            json.dump(current, f, ensure_ascii=False, indent=2)
            f.truncate()

        print("--- Done! ---")

def tts(reply):
    reply = str(reply)

    # sanitize LLM's reply for TTS
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
    global context_file_path
    context_file_path = args.contextfile
    result = prompt_llm(args.prompt,args.debug)
    
    if isinstance(result, tuple):
        reply, tool_context_entries = result
    else:
        reply, tool_context_entries = result, None
    
    print(reply)
    if not args.no_tts:
        tts(reply)
    if not args.no_save:
        # Build complete context entries including the final assistant response
        if tool_context_entries:
            # Add the final assistant response to the tool context entries
            tool_context_entries.append({"role": "assistant", "content": reply})
            save_context(args.prompt, None, tool_context_entries)
        else:
            save_context(args.prompt, reply, None)
    update_memory_if_required()
    
if __name__ == "__main__":
    main()
