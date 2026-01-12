import os
import subprocess
from flask import Flask, request

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

           --= ONLINE =--
""")

# Example usage with curl:
# curl -X POST http://127.0.0.1:5000/run \
#    -H "Content-Type: application/json" \
#    -d '{"prompt":"Tell me Golden Pothos facts.","args":["-notts"]}'

app = Flask(__name__)

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
        timeout=180
    )

    return app.response_class(
        response=result.stdout,
        status=200,
        mimetype="text/plain"
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
