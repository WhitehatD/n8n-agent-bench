#!/usr/bin/env bash
# Build one task's base tree in /work/base/<id>, inside the INSTALLER container:
# the parent commit of the merged fix, dependencies installed, the target package's
# workspace dependencies built. The held-out tests are not added; they stay in the mirror.
# Usage: harness/prepare.sh <task-id>
set -euo pipefail
export MSYS_NO_PATHCONV=1
cd "$(dirname "$0")/.."
id="$1"
read -r base pkg < <(PYTHONUTF8=1 python -c "
import json,sys
t=next(x for x in json.load(open('tasks/tasks.json',encoding='utf-8')) if x['id']==sys.argv[1])
print(t['base_sha'], t['package'])" "$id" | tr -d '\r')

ix() { docker compose exec -T installer "$@"; }
dir="/work/base/$id"
ix sh -c "rm -rf $dir && mkdir -p $dir"
git -C cache/n8n.git -c core.autocrlf=false archive --format=tar "$base" | ix tar -x -C "$dir"
# One commit of history, so the agent's change is exactly `git diff`.
ix sh -c "cd $dir && git init -q && git add -A && git -c user.name=bench -c user.email=bench@local commit -qm base"
ix sh -c "cd $dir && pnpm install --frozen-lockfile --prefer-offline --reporter=silent"
name=$(ix sh -c "node -p \"require('$dir/$pkg/package.json').name\"" | tr -d '\r')
ix sh -c "cd $dir && pnpm turbo run build --filter='$name^...' --filter='!n8n-editor-ui' --filter='!@n8n/chat' --concurrency=2 --output-logs=errors-only > /dev/null"
echo "prepared $id at $base ($name)"
ix sh -c "touch $dir/.prepared"
