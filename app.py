import os
import subprocess
import json
from flask import Flask, jsonify, request
from flask_cors import CORS

print("""
    _/_/_/    _/_/_/    _/_/_/  _/_/_/_/_/  _/_/_/_/_/  _/        _/_/_/_/   
   _/    _/  _/    _/    _/          _/          _/    _/        _/          
  _/    _/  _/_/_/      _/        _/          _/      _/        _/_/_/       
 _/    _/  _/    _/    _/      _/          _/        _/        _/            
_/_/_/    _/    _/  _/_/_/  _/_/_/_/_/  _/_/_/_/_/  _/_/_/_/  _/_/_/_/       
                                                                             
                                    
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

@app.route("/run", methods=["POST"])
def run_prompt():
    data = request.get_json(force=True)

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

    return app.response_class(
        response=result.stdout,
        status=200,
        mimetype="text/plain"
    )


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()

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
        return jsonify({"error": result.stderr.strip() or "Prompt failed"}), 500

    return jsonify({"reply": result.stdout.strip()})


@app.route("/delete-conversation/<conversation_name>", methods=["DELETE"])
def handle_delete_conversation(conversation_name):
    state_dir = os.path.join(os.path.dirname(__file__), "state")
    conversation_path = os.path.join(state_dir, conversation_name)

    if not os.path.exists(conversation_path):
        return jsonify({"error": f"Conversation '{conversation_name}' not found"}), 404

    try:
        os.remove(conversation_path)
        return jsonify({"message": f"Conversation '{conversation_name}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to delete conversation: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
