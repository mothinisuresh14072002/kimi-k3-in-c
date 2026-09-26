import subprocess

def ask_kimi(prompt: str, max_tokens: int = 32) -> str:
    """
    Calls the Kimi-K3 C engine via subprocess and returns the generated text.
    """
    
    # Define the exact paths to your downloaded model and compiled engine
    engine_path = "E:/kimi-k3-in-c/bin/k3"
    model_dir   = "E:/k3model"
    trunk_dir   = "E:/k3trunk"
    
    # Build the command arguments
    command = [
        engine_path, model_dir,
        "--trunk", trunk_dir,
        "--preset", "ultra",          # Uses ultra-low-memory to fit into ~9GB RAM
        "--tok", model_dir,
        "--prompt", prompt,
        "--gen", str(max_tokens),
        "--incremental"               # Use caching for faster generation
    ]
    
    try:
        print(f"Thinking about: '{prompt}'...")
        
        # Run the C engine and capture the output
        result = subprocess.run(
            command, 
            capture_output=True, 
            text=True, 
            check=True
        )
        
        raw_output = result.stdout
        
        # The engine wraps its output in "--- generated text ---" headers.
        # Let's cleanly extract just the text.
        if "--- generated text ---" in raw_output:
            parts = raw_output.split("--- generated text ---")
            if len(parts) > 1:
                clean_text = parts[1].split("----------------------")[0].strip()
                return clean_text
            
        return raw_output.strip()

    except subprocess.CalledProcessError as e:
        print(f"Error running model! Code: {e.returncode}")
        print(f"Error output:\n{e.stderr}")
        return ""
    except FileNotFoundError:
        print(f"Could not find the K3 engine at {engine_path}. Did you run 'make -j'?")
        return ""

# --- Example Usage ---
if __name__ == "__main__":
    prompt = "The capital city of France is"
    
    answer = ask_kimi(prompt, max_tokens=10)
    
    print("\n[Response]")
    print(answer)
