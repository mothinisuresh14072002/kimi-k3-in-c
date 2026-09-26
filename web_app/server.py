#!/usr/bin/env python3
import http.server
import socketserver
import json
import os
import subprocess
import sys
import tempfile

PORT = 8000
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

class KimiHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(HERE, "public"), **kwargs)

    def do_POST(self):
        if self.path == "/api/generate":
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            try:
                data = json.loads(post_data.decode('utf-8'))
                prompt = data.get("prompt", "Hello Kimi")
                gen_count = int(data.get("gen", 16))
                preset = data.get("preset", "laptop")
                
                # Check for model path (env var, E: drive, tiny_ckpt, or ~/k3model)
                model_dir = os.environ.get("K3_MODEL_DIR")
                if not model_dir or not os.path.exists(model_dir):
                    candidates = [
                        os.path.join(ROOT, "scratch", "tiny_ckpt"),
                        r"E:\k3model",
                        os.path.join(ROOT, "models"),
                        os.path.expanduser("~/k3model")
                    ]
                    model_dir = next((c for c in candidates if os.path.exists(c)), r"E:\k3model")

                # Prepare IDs from prompt bytes if no tokenizer files present
                prompt_ids = [ord(c) % 256 for c in prompt]
                ids_str = ",".join(str(i) for i in prompt_ids)
                
                out_json = os.path.join(ROOT, "k3_run.json")
                if os.path.exists(out_json):
                    try: os.remove(out_json)
                    except: pass

                # Run bin/k3
                bin_path = os.path.join(ROOT, "bin", "k3.exe")
                if not os.path.exists(bin_path):
                    bin_path = os.path.join(ROOT, "bin", "k3")
                
                import platform
                is_windows = platform.system() == "Windows"
                active_model_dir = "E:/k3model" if is_windows else os.path.expanduser("~/k3model")
                active_trunk_dir = "E:/k3trunk" if is_windows else os.path.expanduser("~/k3trunk")
                active_preset = "ultra" if is_windows else preset # Let Linux use the requested preset

                cmd = [
                    bin_path, active_model_dir,
                    "--trunk", active_trunk_dir,
                    "--preset", active_preset,
                    "--tok", active_model_dir,
                    "--prompt", prompt,
                    "--gen", str(gen_count),
                    "--incremental",
                    "--out", out_json
                ]

                env = os.environ.copy()
                mingw_bin = r"C:\msys64\mingw64\bin"
                if os.path.exists(mingw_bin):
                    env["PATH"] = mingw_bin + ";" + env.get("PATH", "")

                proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
                
                run_stats = {}
                if os.path.exists(out_json):
                    with open(out_json, "r") as f:
                        run_stats = json.load(f)

                gen_ids = run_stats.get("generated_ids", [])
                
                # Extract clean generated text from engine stdout
                raw_output = proc.stdout
                gen_text = ""
                if "--- generated text ---" in raw_output:
                    parts = raw_output.split("--- generated text ---")
                    if len(parts) > 1:
                        gen_text = parts[1].split("----------------------")[0].strip()

                response = {
                    "success": proc.returncode == 0,
                    "prompt": prompt,
                    "prompt_ids": prompt_ids,
                    "generated_text": gen_text,
                    "generated_ids": gen_ids,
                    "stats": run_stats,
                    "stdout": proc.stdout[-500:],
                    "stderr": proc.stderr[-500:]
                }

                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode('utf-8'))

            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_error(404, "Not Found")

    def do_GET(self):
        if self.path == "/api/status":
            bin_path = os.path.join(ROOT, "bin", "k3.exe")
            tiny_ckpt = os.path.join(ROOT, "scratch", "tiny_ckpt")
            status = {
                "engine_built": os.path.exists(bin_path) or os.path.exists(os.path.join(ROOT, "bin", "k3")),
                "tiny_ckpt_ready": os.path.exists(tiny_ckpt),
                "model_name": "Kimi K3 (2.78 Trillion MoE)",
                "active_checkpoint": "scratch/tiny_ckpt (Synthetic 13-Layer Fixture)" if os.path.exists(tiny_ckpt) else "Full Checkpoint"
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode('utf-8'))
        else:
            super().do_GET()

def run_server():
    os.makedirs(os.path.join(HERE, "public"), exist_ok=True)
    with socketserver.TCPServer(("", PORT), KimiHandler) as httpd:
        print(f"Kimi K3 Web Server active at http://localhost:{PORT}")
        httpd.serve_forever()

if __name__ == "__main__":
    run_server()
