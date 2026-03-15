import os
import subprocess
import json
import re
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, jsonify, request
from flask_cors import CORS

print("""
    _/_/_/    _/_/_/    _/_/_/  _/_/_/_/_/  _/_/_/_/_/  _/        _/_/_/_/   
   _/    _/  _/    _/    _/          _/          _/    _/        _/          
  _/    _/  _/_/_/      _/        _/          _/      _/        _/_/_/       
 _/    _/  _/    _/    _/      _/          _/        _/        _/            
/_/_/    _/    _/  _/_/_/  _/_/_/_/_/  _/_/_/_/_/  _/_/_/_/  _/_/_/_/       
                                                                              
                                     
    _/      _/  _/_/_/_/    _/_/    
   _/_/    _/  _/        _/    _/   
  _/  _/  _/  _/_/_/    _/    _/    
 _/    _/_/  _/        _/    _/     
_/      _/  _/_/_/_/    _/_/        
""")

# Example usage with curl:
# curl -X POST http://127.0.0.1:5000/run \
#    -H "Content-Type: application/json" \
#    -d '{"prompt":"Tell me Golden Pothos facts.","args":["-notts"]}'

app = Flask(__name__)
CORS(app)

log_file = os.path.join(os.path.dirname(__file__), "log.txt")
file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s'))
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('Drizzle NEO server starting up')

@app.route("/run", methods=["POST"])
def run_prompt():
    data = request.get_json(force=True)
    app.logger.info(f"POST /run: prompt={data.get('prompt', '')[:100]}, args={data.get('args', [])}")

    prompt = data["prompt"]
    args = data.get("args", [])

    cmd = ["python", "prompt.py", "-p", prompt] + args

    result = subprocess.run(
        cmd,
        cwd=os.path.dirname(__file__),  # ensures prompt.py is found
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode == 0:
        app.logger.info(f"POST /run: Success - {len(result.stdout)} bytes returned")
    else:
        app.logger.error(f"POST /run: Failed - {result.stderr}")

    return app.response_class(
        response=result.stdout,
        status=200,
        mimetype="text/plain"
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    app.logger.info(f"POST /chat: text={text[:100]}")

    if not text:
        return jsonify({"error": "Missing text"}), 400

    cmd = ["python", "prompt.py", "-p", text]

    result = subprocess.run(
        cmd,
        cwd=os.path.dirname(__file__),
        capture_output=True,
        text=True,
        timeout=300
    )

    if result.returncode != 0:
        app.logger.error(f"POST /chat: Failed - {result.stderr}")
        return jsonify({"error": result.stderr.strip() or "Prompt failed"}), 500

    app.logger.info(f"POST /chat: Success - {len(result.stdout)} bytes returned")
    return jsonify({"reply": result.stdout.strip()})


@app.route("/delete-conversation/<conversation_name>", methods=["DELETE"])
def handle_delete_conversation(conversation_name):
    app.logger.info(f"DELETE /delete-conversation/{conversation_name}")
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    conversation_path = os.path.join(state_dir, conversation_name)

    if not os.path.exists(conversation_path):
        app.logger.warning(f"DELETE /delete-conversation/{conversation_name}: Not found")
        return jsonify({"error": f"Conversation '{conversation_name}' not found"}), 404

    try:
        os.remove(conversation_path)
        app.logger.info(f"DELETE /delete-conversation/{conversation_name}: Success")
        return jsonify({"message": f"Conversation '{conversation_name}' deleted successfully"}), 200
    except Exception as e:
        app.logger.error(f"DELETE /delete-conversation/{conversation_name}: Failed - {str(e)}")
        return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500


@app.route("/config", methods=["GET"])
def get_config():
    app.logger.info("GET /config")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        return jsonify(config)
    except Exception as e:
        app.logger.error(f"GET /config: Failed - {str(e)}")
        return jsonify({"error": f"Failed to read config: {str(e)}"}), 500


def _deep_merge(base, update):
    result = base.copy()
    for key, value in update.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


@app.route("/config", methods=["PUT"])
def update_config():
    app.logger.info("PUT /config")
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        updates = request.get_json(force=True)
        with open(config_path, "r") as f:
            current_config = json.load(f)
        merged_config = _deep_merge(current_config, updates)
        with open(config_path, "w") as f:
            json.dump(merged_config, f, indent=4)
        app.logger.info("PUT /config: Success")
        return jsonify({"message": "Config updated successfully"})
    except Exception as e:
        app.logger.error(f"PUT /config: Failed - {str(e)}")
        return jsonify({"error": f"Failed to update config: {str(e)}"}), 500


@app.route("/state", methods=["GET"])
def list_state_files():
    app.logger.info("GET /state")
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    try:
        files = [f for f in os.listdir(state_dir) if os.path.isfile(os.path.join(state_dir, f))]
        app.logger.info(f"GET /state: Found {len(files)} files")
        return jsonify({"files": files})
    except Exception as e:
        app.logger.error(f"GET /state: Failed - {str(e)}")
        return jsonify({"error": f"Failed to list files: {str(e)}"}), 500


@app.route("/state/copy", methods=["POST"])
def copy_state_file():
    data = request.get_json(force=True) or {}
    source_filename = data.get("name")
    app.logger.info(f"POST /state/copy: source={source_filename}")

    if not source_filename:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    state_dir = os.path.join(os.path.dirname(__file__), "state")
    source_path = os.path.join(state_dir, source_filename)

    if not os.path.exists(source_path) or not os.path.isfile(source_path):
        app.logger.warning(f"POST /state/copy: File not found - {source_filename}")
        return jsonify({"error": f"File '{source_filename}' not found in state directory"}), 404

    base_name, extension = os.path.splitext(source_filename)

    match = re.search(r"(\d+)$", base_name)
    if match:
        base_without_num = base_name.rsplit('.', 1)[0]
    else:
        base_without_num = base_name

    existing_nums = []
    for f in os.listdir(state_dir):
        f_match = re.search(rf"^{re.escape(base_without_num)}\.(\d+){re.escape(extension)}$", f)
        if f_match:
            existing_nums.append(int(f_match.group(1)))

    if existing_nums:
        next_num = max(existing_nums) + 1
    else:
        next_num = 1

    new_filename = f"{base_without_num}.{next_num}{extension}"
    dest_path = os.path.join(state_dir, new_filename)

    try:
        with open(source_path, "r") as src_file:
            content = src_file.read()
        with open(dest_path, "w") as dest_file:
            dest_file.write(content)
        app.logger.info(f"POST /state/copy: Copied '{source_filename}' to '{new_filename}'")
        return jsonify({"message": f"Copied '{source_filename}' to '{new_filename}'"}), 200
    except Exception as e:
        app.logger.error(f"POST /state/copy: Failed - {str(e)}")
        return jsonify({"error": f"Failed to copy file: {str(e)}"}), 500


@app.route("/state/<filename>", methods=["GET"])
def get_state_file(filename):
    app.logger.info(f"GET /state/{filename}")
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    file_path = os.path.join(state_dir, filename)

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        app.logger.warning(f"GET /state/{filename}: File not found")
        return jsonify({"error": f"File '{filename}' not found in state directory"}), 404

    try:
        with open(file_path, "r") as f:
            content = f.read()
        app.logger.info(f"GET /state/{filename}: Success - {len(content)} bytes")
        return jsonify({"filename": filename, "content": content})
    except Exception as e:
        app.logger.error(f"GET /state/{filename}: Failed - {str(e)}")
        return jsonify({"error": f"Failed to read file: {str(e)}"}), 500


@app.route("/state/<filename>", methods=["PUT"])
def update_state_file(filename):
    app.logger.info(f"PUT /state/{filename}")
    data = request.get_json(force=True) or {}
    content = data.get("content", "")
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    file_path = os.path.join(state_dir, filename)

    try:
        with open(file_path, "w") as f:
            f.write(content)
        app.logger.info(f"PUT /state/{filename}: Success - {len(content)} bytes")
        return jsonify({"message": f"File '{filename}' updated successfully"})
    except Exception as e:
        app.logger.error(f"PUT /state/{filename}: Failed - {str(e)}")
        return jsonify({"error": f"Failed to update file: {str(e)}"}), 500


@app.route("/memory", methods=["PUT"])
def update_memory():
    data = request.get_json(force=True) or {}
    content = data.get("content", "")
    app.logger.info(f"PUT /memory: {len(content)} bytes")

    memory_path = os.path.join(os.path.dirname(__file__), "state", "memory.txt")

    try:
        with open(memory_path, "w") as f:
            f.write(content)
        app.logger.info("PUT /memory: Success")
        return jsonify({"message": "Memory updated successfully"})
    except Exception as e:
        app.logger.error(f"PUT /memory: Failed - {str(e)}")
        return jsonify({"error": f"Failed to update memory: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
