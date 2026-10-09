"""
TrailMate AI - LLM Service

Generates text by invoking the local SmolLM2-Instruct model through
llama-cli (llama.cpp) as a subprocess.

Design decisions:
- No external HTTP calls, no Ollama, no proprietary API.
- No Python-level model loading (Transformers / llama-cpp-python).
- llama-cli caches the HuggingFace GGUF locally after the first pull,
  so subsequent calls are instant-start with no re-download.
- The function is intentionally synchronous; FastAPI will dispatch it
  to a thread-pool worker when called from a sync route handler.

Flags used (all confirmed working in llama.cpp build b11406):
  -p PROMPT     Set the initial prompt text
  -n N          Maximum tokens to predict, then exit
  --hf-repo     HuggingFace repo to pull the GGUF from (uses local cache)
  --hf-file     Specific GGUF file inside that repo

stdin=DEVNULL is the critical flag that prevents llama-cli from waiting
for interactive input — without it the process never exits.
"""

import shutil
import subprocess

from backend.app.config import settings

# ── SmolLM2-Instruct uses the ChatML template ─────────────────────────────────

_SYSTEM_PROMPT = (
    "You are TrailMate, a concise and enthusiastic outdoor adventure assistant. "
    "Give practical, actionable advice."
)

# The marker that ends the prompt and where the assistant reply begins
_ASSISTANT_MARKER = "<|im_start|>assistant\n"
_STOP_TOKEN = "<|im_end|>"


def build_chat_prompt(user_message: str, system: str = _SYSTEM_PROMPT) -> str:
    """
    Public utility: wrap a user message in the SmolLM2-Instruct ChatML format.

    Args:
        user_message: The raw user-facing text.
        system:       System prompt to use. Defaults to the TrailMate generic prompt.

    Returns:
        A fully-formatted ChatML string ready to pass to llama-cli via ``-p``.
    """
    return (
        f"<|im_start|>system\n{system}<|im_end|>\n"
        f"<|im_start|>user\n{user_message.strip()}<|im_end|>\n"
        f"{_ASSISTANT_MARKER}"
    )


def _extract_response(raw_stdout: str, formatted_prompt: str) -> str:
    """
    Extract only the assistant-generated text from llama-cli stdout.

    llama-cli echoes the full prompt to stdout before the generated text
    (when --no-display-prompt is not used). We find the assistant marker
    and take everything after it, then strip stop-tokens and whitespace.
    """
    # Find the last occurrence of the assistant marker (most robust)
    idx = raw_stdout.rfind(_ASSISTANT_MARKER)
    if idx != -1:
        response = raw_stdout[idx + len(_ASSISTANT_MARKER):]
    elif raw_stdout.startswith(formatted_prompt):
        # Fallback: strip the echoed prompt prefix directly
        response = raw_stdout[len(formatted_prompt):]
    else:
        # Last resort: return everything
        response = raw_stdout

    return response.replace(_STOP_TOKEN, "").strip()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_text(prompt: str, max_tokens: int | None = None) -> str:
    """
    Generate a text response from the local SmolLM2-Instruct model.

    The ``prompt`` argument is passed as-is to llama-cli. Callers are
    responsible for formatting (use :func:`build_chat_prompt` to build a
    ChatML-formatted prompt, or supply any other raw text).

    Args:
        prompt:     A fully-formatted prompt string (e.g. ChatML).
        max_tokens: Optional override for the token generation limit.
                    Falls back to ``settings.llm_max_tokens`` when omitted.

    Returns:
        The model's generated response as a stripped plain string.

    Raises:
        RuntimeError: If ``llama-cli`` is not found on PATH, exits non-zero,
                      or exceeds the configured timeout.
    """
    # ── Locate the binary ─────────────────────────────────────────────────────
    llama_bin = shutil.which("llama-cli")
    if not llama_bin:
        raise RuntimeError(
            "llama-cli not found on PATH. "
            "Ensure llama.cpp is installed and llama-cli is accessible."
        )

    tokens = max_tokens if max_tokens is not None else settings.llm_max_tokens
    formatted_prompt = prompt  # caller is responsible for formatting

    # ── Build command ─────────────────────────────────────────────────────────
    # Only use flags that are confirmed to work in build b11406.
    # -p / -n are the stable short forms; long aliases vary by build.
    cmd = [
        llama_bin,
        "--hf-repo", settings.llm_hf_repo,
        "--hf-file", settings.llm_hf_file,
        "-p", formatted_prompt,   # initial prompt (ChatML or plain)
        "-n", str(tokens),        # tokens to generate, then EXIT
    ]

    # ── Run subprocess ────────────────────────────────────────────────────────
    try:
        result = subprocess.run(
            cmd,
            # CRITICAL: close stdin so llama-cli never waits for interactive
            # input — without this it hangs forever and triggers the timeout.
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,    # swallow llama.cpp log noise
            text=True,
            encoding="utf-8",          # llama-cli outputs UTF-8; on Windows
            errors="replace",          # text=True alone defaults to cp1252
            timeout=settings.llm_timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            f"llama-cli timed out after {settings.llm_timeout}s."
        ) from exc
    except FileNotFoundError as exc:
        raise RuntimeError(
            f"llama-cli binary not executable: {llama_bin}"
        ) from exc

    if result.returncode != 0:
        snippet = result.stderr[:400].strip()
        raise RuntimeError(
            f"llama-cli exited with code {result.returncode}. "
            f"Details: {snippet}"
        )

    return _extract_response(result.stdout, formatted_prompt)
