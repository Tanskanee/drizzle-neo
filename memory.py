import os
import json
from pathlib import Path
from openai import OpenAI

def update_memory_if_required(memory_model, memory_prompt, memory_maxmsgs, memory, server_url, context_file_path, load_context_func):
    context = load_context_func()
    n_lines = int(memory_maxmsgs / 2)

    if len(context.get("history", [])) > memory_maxmsgs:
        print(f"--- Context exceeds maximum length ({len(context.get('history', []))}/{memory_maxmsgs})! Pruning and updating context to {n_lines} messages, this may take a while... ---")

        # Construct messages for the memory update
        messages = [{"role": "system", "content": memory_prompt}]
        messages.append({"role": "user", "content": "The conversation: " + str(context)})
        messages.append({"role": "user", "content": "The current memory file: " + memory})

        apikey = os.getenv("OPENAI_API_KEY")
        if apikey is None:
            apikey = ""

        client = OpenAI(
            base_url = server_url,
            api_key = str(apikey),
        )
        completion = client.chat.completions.create(
            model=memory_model,
            messages=messages
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