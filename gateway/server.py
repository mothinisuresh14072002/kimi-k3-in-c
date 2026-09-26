#!/usr/bin/env python3
"""
gateway/server.py - Centralized OpenAI-Compatible API Gateway for Kimi K3.

Exposes OpenAI standard endpoints:
  - POST /v1/chat/completions
  - GET  /v1/models
  - GET  /health
"""
import os
import sys
import time
import json
import uuid
import subprocess
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

app = FastAPI(
    title="Kimi K3 OpenAI API Gateway",
    description="Central AI Inference Gateway for Kimi K3 (2.78T MoE Model)",
    version="1.0.0"
)

# Enable CORS for cross-project & web client access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str = Field(..., description="role: system, user, or assistant")
    content: str = Field(..., description="message text content")

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field("kimi-k3", description="model ID")
    messages: List[ChatMessage] = Field(..., description="list of conversation messages")
    max_tokens: Optional[int] = Field(16, description="maximum tokens to generate")
    temperature: Optional[float] = Field(0.7, description="sampling temperature")
    preset: Optional[str] = Field("laptop", description="memory preset: laptop, desktop, server, ultra")

@app.get("/health")
def health_check():
    bin_path = os.path.join(ROOT, "bin", "k3.exe")
    if not os.path.exists(bin_path):
        bin_path = os.path.join(ROOT, "bin", "k3")
    
    env_model = os.environ.get("K3_MODEL_DIR")
    if env_model and os.path.exists(env_model):
        active_ckpt = env_model
    else:
        candidates = [
            os.path.join(ROOT, "scratch", "tiny_ckpt"),
            r"E:\k3model",
            os.path.join(ROOT, "models"),
            os.path.expanduser("~/k3model")
        ]
        active_ckpt = next((c for c in candidates if os.path.exists(c)), r"E:\k3model")

    return {
        "status": "online",
        "service": "Kimi K3 OpenAI Gateway",
        "engine_executable": bin_path,
        "engine_ready": os.path.exists(bin_path),
        "active_checkpoint": active_ckpt,
        "supported_presets": ["laptop", "desktop", "workstation", "server", "ultra"]
    }

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "kimi-k3",
                "object": "model",
                "created": 1725890000,
                "owned_by": "moonshot-ai",
                "permission": [],
                "root": "kimi-k3",
                "parent": None
            },
            {
                "id": "kimi-k3-2.78t",
                "object": "model",
                "created": 1725890000,
                "owned_by": "moonshot-ai",
                "permission": [],
                "root": "kimi-k3",
                "parent": None
            }
        ]
    }

@app.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    try:
        # Build prompt from message history
        prompt_parts = []
        for msg in req.messages:
            if msg.role == "system":
                prompt_parts.append(f"[System]: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"[User]: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"[Assistant]: {msg.content}")
        
        full_prompt = "\n".join(prompt_parts)
        if not full_prompt:
            full_prompt = "Hello"

        # Locate model directory
        model_dir = os.environ.get("K3_MODEL_DIR")
        if not model_dir or not os.path.exists(model_dir):
            candidates_model = [
                r"E:\k3model",
                os.path.join(ROOT, "scratch", "tiny_ckpt"),
                os.path.join(ROOT, "models"),
                os.path.expanduser("~/k3model")
            ]
            model_dir = next((c for c in candidates_model if os.path.exists(c)), r"E:\k3model")

        # Locate trunk directory
        trunk_dir = os.environ.get("K3_TRUNK_DIR")
        if not trunk_dir or not os.path.exists(trunk_dir):
            candidates_trunk = [
                r"E:\k3trunk",
                os.path.join(ROOT, "scratch", "tiny_ckpt"),
                os.path.join(ROOT, "trunk"),
                os.path.expanduser("~/k3trunk")
            ]
            trunk_dir = next((c for c in candidates_trunk if os.path.exists(c)), None)

        preset = req.preset or os.environ.get("K3_PRESET", "auto")

        out_json = os.path.join(ROOT, "k3_run.json")
        if os.path.exists(out_json):
            try: os.remove(out_json)
            except: pass

        # Locate bin/k3
        bin_path = os.path.join(ROOT, "bin", "k3.exe")
        if not os.path.exists(bin_path):
            bin_path = os.path.join(ROOT, "bin", "k3")

        if not os.path.exists(bin_path):
            raise HTTPException(status_code=500, detail=f"C Engine binary not found at {bin_path}")

        cmd = [
            bin_path, model_dir,
            "--prompt", full_prompt,
            "--tok", model_dir,
            "--gen", str(req.max_tokens or 16),
            "--preset", preset,
            "--incremental",
            "--out", out_json
        ]
        if trunk_dir:
            cmd.extend(["--trunk", trunk_dir])

        env = os.environ.copy()
        mingw_bin = r"C:\msys64\mingw64\bin"
        if os.path.exists(mingw_bin):
            env["PATH"] = mingw_bin + ";" + env.get("PATH", "")

        t0 = time.time()
        proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=600, env=env)
        elapsed = time.time() - t0

        if proc.returncode != 0 and not os.path.exists(out_json):
            raise HTTPException(status_code=500, detail=f"Engine execution failed: {proc.stderr[-500:]}")

        run_stats = {}
        if os.path.exists(out_json):
            with open(out_json, "r") as f:
                run_stats = json.load(f)

        generated_text = run_stats.get("generated_text")
        if not generated_text:
            gen_ids = run_stats.get("generated_ids", [])
            chars = []
            for i in gen_ids:
                if 32 <= i <= 126 or i in (10, 13, 9):
                    chars.append(chr(i))
                else:
                    chars.append(f"[{i}]")
            generated_text = "".join(chars)

        created_ts = int(time.time())
        chat_id = f"chatcmpl-kimi-{uuid.uuid4().hex[:12]}"

        prompt_ids = run_stats.get("prompt_ids", [])
        gen_ids = run_stats.get("generated_ids", [])

        # Standard OpenAI Response Payload
        return {
            "id": chat_id,
            "object": "chat.completion",
            "created": created_ts,
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": generated_text
                    },
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": len(prompt_ids),
                "completion_tokens": len(gen_ids),
                "total_tokens": len(prompt_ids) + len(gen_ids)
            },
            "system_telemetry": {
                "peak_rss_mb": round(run_stats.get("peak_rss_bytes", 0) / 1024 / 1024, 2),
                "seconds_per_token": run_stats.get("seconds_per_token", 0.0),
                "wall_seconds": round(elapsed, 3)
            }
        }

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
