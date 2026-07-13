#!/usr/bin/env python3
"""
Auto-save session transcript to LLM/ directory as Markdown.
Triggered by Stop hook after each Claude response.
"""

import json
import sys
import os
from datetime import datetime
from pathlib import Path

# A single log file is capped so that a long-running session cannot grow
# unbounded. Vault indexers (Obsidian) choke on multi-megabyte Markdown.
DEFAULT_MAX_BYTES = 1_000_000

# Headroom kept aside for the truncation notice when messages are dropped.
NOTICE_RESERVE_BYTES = 512

def byte_len(text: str) -> int:
    return len(text.encode('utf-8'))

def parse_transcript(transcript_path: str) -> list:
    """Parse JSONL transcript file and extract conversation."""
    messages = []
    expanded_path = os.path.expanduser(transcript_path)

    if not os.path.exists(expanded_path):
        return messages

    with open(expanded_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                entry_type = entry.get('type')

                # Extract user input (type: 'user' in transcript)
                # Skip tool results (entries with 'toolUseResult' key)
                if entry_type == 'user' and 'toolUseResult' not in entry:
                    content = entry.get('message', {}).get('content', '')
                    if isinstance(content, str) and content.strip():
                        # Direct user input as string
                        messages.append({'role': 'user', 'content': content.strip()})
                    elif isinstance(content, list):
                        # Handle content blocks (but skip tool_result blocks)
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict):
                                # Only extract text blocks, skip tool_result
                                if block.get('type') == 'text':
                                    text_parts.append(block.get('text', ''))
                            elif isinstance(block, str):
                                text_parts.append(block)
                        if text_parts:
                            content = '\n'.join(text_parts)
                            if content.strip():
                                messages.append({'role': 'user', 'content': content.strip()})

                # Extract Claude's response
                elif entry_type == 'assistant':
                    content = entry.get('message', {}).get('content', '')
                    if isinstance(content, list):
                        text_parts = []
                        for block in content:
                            if isinstance(block, dict) and block.get('type') == 'text':
                                text_parts.append(block.get('text', ''))
                        content = '\n'.join(text_parts)
                    if content and content.strip():
                        messages.append({'role': 'assistant', 'content': content.strip()})
            except json.JSONDecodeError:
                continue

    return messages

def resolve_log_dir(cwd: str) -> Path:
    """Resolve the directory to write the log into.

    Defaults to LLM/ under the session's working directory. Set
    OBSIDIAN_LLM_LOG_DIR to redirect logs elsewhere (e.g. outside an
    Obsidian vault, so the vault does not have to index them).
    """
    override = os.environ.get('OBSIDIAN_LLM_LOG_DIR', '').strip()
    if override:
        return Path(os.path.expanduser(override))
    return Path(cwd) / 'LLM'

def resolve_max_bytes() -> int:
    """Resolve the size cap for a single log file. 0 means unlimited."""
    raw = os.environ.get('OBSIDIAN_LLM_LOG_MAX_BYTES', '').strip()
    if not raw:
        return DEFAULT_MAX_BYTES
    try:
        return max(int(raw), 0)
    except ValueError:
        return DEFAULT_MAX_BYTES

def render_message(msg: dict) -> str:
    role = "**User**" if msg['role'] == 'user' else "**Claude**"
    return f"## {role}\n\n{msg['content']}\n\n---\n\n"

def generate_markdown(messages: list, session_id: str, cwd: str,
                      max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    """Convert messages to Markdown, keeping the file within max_bytes.

    The whole transcript is rewritten on every turn, so a long-lived session
    (e.g. a resident agent) would otherwise grow without bound. When the log
    exceeds max_bytes, the oldest messages are dropped so the most recent
    exchanges are always the ones kept.
    """
    now = datetime.now()

    header = f"""# Session Log

- Session ID: {session_id}
- Date: {now.strftime('%Y-%m-%d %H:%M')}
- Directory: {cwd}

---

"""

    rendered = [render_message(msg) for msg in messages]

    if not max_bytes:
        return header + ''.join(rendered)

    # Reserve room for the header and a possible truncation notice.
    budget = max_bytes - byte_len(header) - NOTICE_RESERVE_BYTES

    kept = []
    used = 0
    for chunk in reversed(rendered):
        size = byte_len(chunk)
        if used + size > budget:
            break
        kept.append(chunk)
        used += size
    kept.reverse()

    # A single message can exceed the whole budget on its own; keep a
    # truncated tail of the latest one rather than writing an empty log.
    if not kept and rendered:
        tail = rendered[-1].encode('utf-8')[-max(budget, 0):]
        kept = [tail.decode('utf-8', errors='ignore')]

    dropped = len(rendered) - len(kept)
    if not dropped:
        return header + ''.join(kept)

    notice = (
        f"> [!warning] 古いメッセージ {dropped} 件を省略しました\n"
        f"> このログは {max_bytes:,} バイトの上限に収めるため、直近 {len(kept)} 件のみを保持しています。\n"
        f"> 全文は Claude Code の transcript を参照してください。\n"
        f"> 上限は環境変数 `OBSIDIAN_LLM_LOG_MAX_BYTES` で変更できます（`0` で無制限）。\n\n"
    )

    return header + notice + ''.join(kept)

def main():
    # Read hook input from stdin
    try:
        hook_input = json.loads(sys.stdin.read())
    except json.JSONDecodeError:
        sys.exit(0)
    
    transcript_path = hook_input.get('transcript_path', '')
    session_id = hook_input.get('session_id', 'unknown')
    cwd = hook_input.get('cwd', os.getcwd())
    
    if not transcript_path:
        sys.exit(0)
    
    # Parse transcript
    messages = parse_transcript(transcript_path)
    
    if not messages:
        sys.exit(0)
    
    # Determine save directory (LLM/ under cwd, unless redirected)
    llm_dir = resolve_log_dir(cwd)
    llm_dir.mkdir(parents=True, exist_ok=True)

    # Generate filename with date and session ID
    now = datetime.now()
    filename = f"{now.strftime('%Y-%m-%d')}_{session_id[:8]}.md"
    filepath = llm_dir / filename

    # Generate and save Markdown
    md_content = generate_markdown(messages, session_id, cwd, resolve_max_bytes())

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # Output nothing to avoid interfering with Claude
    sys.exit(0)

if __name__ == '__main__':
    main()
