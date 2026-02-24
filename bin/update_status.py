#!/usr/bin/env python3
"""
Simple helper to update public/status.json and append to logs/agent-activity.log
Usage example:
  python3 bin/update_status.py --task "Update OpenClaw" --step "installing" --detail "npm i -g openclaw" --progress 40 --status running
"""
import argparse, json, time, os
W = os.path.dirname(os.path.dirname(__file__))
STATUS_PATH = os.path.join(W, 'public', 'status.json')
LOG_PATH = os.path.join(W, 'logs', 'agent-activity.log')

parser = argparse.ArgumentParser()
parser.add_argument('--task')
parser.add_argument('--step')
parser.add_argument('--detail')
parser.add_argument('--progress', type=float)
parser.add_argument('--status')
parser.add_argument('--append-log', help='extra message to append to activity log')
args = parser.parse_args()

now = int(time.time()*1000)
# load existing
try:
    with open(STATUS_PATH,'r') as f:
        status = json.load(f)
except Exception:
    status = {'current_task':'idle','step':None,'step_detail':None,'progress':0,'last_status':'ok','recent_logs':[], 'updated': None}

if args.task: status['current_task'] = args.task
if args.step is not None: status['step'] = args.step
if args.detail is not None: status['step_detail'] = args.detail
if args.progress is not None: status['progress'] = args.progress
if args.status is not None: status['last_status'] = args.status
status['updated'] = now
# append recent log (keep last 200)
msg = args.append_log or (args.task or '') + ('. ' + args.detail if args.detail else '')
if msg:
    status.setdefault('recent_logs',[]).insert(0, {'ts': now, 'msg': msg})
    status['recent_logs'] = status['recent_logs'][:200]

# write status file
with open(STATUS_PATH,'w') as f:
    json.dump(status, f, indent=2, ensure_ascii=False)

# append to activity log
with open(LOG_PATH,'a') as lf:
    lf.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}\n")

print('updated', STATUS_PATH)
