#!/bin/sh
# PostToolUse hook: run CI's gating flake8 selection on the edited .py file.
# Prefers flake8 in the running web container (Python matches prod), falls back to .venv.
# Exit 2 feeds the errors back to Claude; anything else is silent.
f=$(jq -r '.tool_response.filePath // .tool_input.file_path // empty')
case "$f" in *.py) ;; *) exit 0 ;; esac
root="${CLAUDE_PROJECT_DIR:-$(pwd)}"
case "$f" in "$root"/*) rel="${f#"$root"/}" ;; *) exit 0 ;; esac
[ -f "$root/$rel" ] || exit 0
cd "$root" || exit 0

select="E9,F63,F7,F82"
if docker compose exec -T web sh -c 'command -v flake8' >/dev/null 2>&1; then
  out=$(docker compose exec -T web flake8 --select="$select" --show-source "$rel" 2>&1)
elif [ -x .venv/bin/flake8 ]; then
  out=$(.venv/bin/flake8 --select="$select" --show-source "$rel" 2>&1)
else
  exit 0
fi
[ -z "$out" ] && exit 0
echo "flake8 (CI-gating errors) in $rel:" >&2
echo "$out" >&2
exit 2
