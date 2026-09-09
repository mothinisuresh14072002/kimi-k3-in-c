#!/usr/bin/env python3
"""
gateway/test_client.py - Verify Kimi K3 Gateway via standard OpenAI Python SDK
"""
import sys
from openai import OpenAI

def main():
    print("Connecting to Kimi K3 OpenAI API Gateway at http://localhost:8001/v1 ...")
    
    # Initialize standard OpenAI client pointing to local Gateway
    client = OpenAI(
        base_url="http://localhost:8001/v1",
        api_key="local-key"
    )

    print("\n--- Fetching Available Models ---")
    models = client.models.list()
    for m in models.data:
        print(f"  - Model ID: {m.id} (owned by {m.owned_by})")

    print("\n--- Sending Chat Completion Request ---")
    messages = [
        {"role": "system", "content": "You are Kimi K3, a 2.78-trillion parameter MoE AI model."},
        {"role": "user", "content": "Explain PostgreSQL indexing"}
    ]
    
    response = client.chat.completions.create(
        model="kimi-k3",
        messages=messages,
        max_tokens=16
    )

    print("\n=== OpenAI SDK Response Received ===")
    print(f"ID        : {response.id}")
    print(f"Model     : {response.model}")
    print(f"Content   : {response.choices[0].message.content}")
    print(f"Usage     : {response.usage.prompt_tokens} prompt + {response.usage.completion_tokens} completion = {response.usage.total_tokens} total tokens")

if __name__ == "__main__":
    main()
