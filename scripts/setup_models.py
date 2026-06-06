import shutil
import subprocess
from pathlib import Path

import psutil

# configuration filepath
ENV_EXAMPLE_PATH = Path(".env.example")
ENV_PATH = Path(".env")


def recommend_model() -> str:
    # choose model using system ram limit
    total_ram_gb = psutil.virtual_memory().total / (1024**3)
    if total_ram_gb >= 8:
        return "llama3"
    elif total_ram_gb >= 4:
        return "qwen2.5:1.5b"
    else:
        return "tinyllama"


def pull_model_ollama(model: str) -> None:
    # pull model using local cli or docker container
    try:
        # query local command directly
        subprocess.run(["ollama", "pull", model], check=True, capture_output=True)
        print(f"pulled model {model} via local ollama cli")
        return
    except (FileNotFoundError, subprocess.CalledProcessError):
        pass

    # fallback to docker container if present
    try:
        subprocess.run(
            ["docker", "exec", "ollama", "ollama", "pull", model],
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"pulled model {model} via docker container 'ollama'")
        return
    except (FileNotFoundError, subprocess.CalledProcessError) as e:
        raise RuntimeError(
            "No running ollama cli or docker container 'ollama' found."
            "Please install ollama or start the container."
        ) from e


def update_env_file(model: str) -> None:
    # update configuration file while preserving other setting
    if not ENV_PATH.exists():
        # copy initial configuration from template
        if ENV_EXAMPLE_PATH.exists():
            shutil.copy(ENV_EXAMPLE_PATH, ENV_PATH)
            print("đã tạo .env từ .env.example")
        else:
            # initialize empty configuration file
            ENV_PATH.write_text("", encoding="utf-8")

    # read config file content
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    new_lines = []
    reasoning_key = "REASONING_MODEL"
    embedding_key = "EMBEDDING_MODEL"
    has_reasoning = False
    has_embedding = False

    for line in lines:
        if line.strip().startswith(reasoning_key + "="):
            new_lines.append(f"{reasoning_key}={model}")
            has_reasoning = True
        elif line.strip().startswith(embedding_key + "="):
            new_lines.append(f"{embedding_key}=nomic-embed-text")
            has_embedding = True
        else:
            new_lines.append(line)

    if not has_reasoning:
        new_lines.append(f"{reasoning_key}={model}")
    if not has_embedding:
        new_lines.append(f"{embedding_key}=nomic-embed-text")

    ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def main() -> None:
    model = recommend_model()
    ram_display = f"{psutil.virtual_memory().total / (1024**3):.1f}"
    print(f"system memory: {ram_display}GB → recommended reasoning model: {model}")
    choice = input(f"pull model '{model}' via ollama and update .env? (y/n): ").strip().lower()
    if choice == "y":
        try:
            pull_model_ollama(model)
            update_env_file(model)
            print(f"successfully updated .env with REASONING_MODEL={model}")
        except Exception as e:
            print(f"setup error: {e}")
    else:
        print("skipped auto configuration. you can manually edit .env later.")


if __name__ == "__main__":
    main()
