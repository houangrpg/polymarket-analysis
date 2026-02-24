#!/usr/bin/env python3
"""
Snapshot status.json (host-side)
- If workspace/status.json exists, copy it to data/status-YYYYMMDD-HHMMSS.json
- Else, produce a small status JSON from system commands
- Commit snapshot to a timestamped branch and push, attempt to create PR with gh if available
"""
import os,sys,shutil,subprocess,datetime,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"
DATA.mkdir(parents=True,exist_ok=True)
now=datetime.datetime.now()
ts=now.strftime('%Y%m%d-%H%M%S')
status_src=ROOT/'status.json'
out=DATA/f'status-{ts}.json'

if status_src.exists():
    shutil.copy2(status_src, out)
    source='status.json'
else:
    # produce minimal snapshot
    def run(cmd):
        try:
            r=subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
            return r.stdout.strip()
        except Exception as e:
            return str(e)
    j={}
    j['generated']=now.isoformat()
    j['system']={}
    j['system']['uname']=run('uname -a')
    j['system']['uptime']=run('uptime -p')
    j['cpu']={'usage': None}
    j['memory']={'free': run("free -h | sed -n '2p'" )}
    j['disk']={'df': run("df -h / | sed -n '2p'")}
    # services
    j['services']={}
    j['services']['openclaw']={'ok': True, 'msg': 'generated snapshot'}
    out.write_text(json.dumps(j,indent=2),encoding='utf-8')
    source='generated'

# Git: create branch, add file, commit, push
os.chdir(ROOT)
branch=f'maintenance/snapshot-{ts}'
# create branch
subprocess.run(['git','fetch','--all'])
subprocess.run(['git','checkout','-b',branch])
subprocess.run(['git','add',str(out)])
cm=f'Add status snapshot {out.name}'
subprocess.run(['git','commit','-m',cm])
# push branch
push_proc=subprocess.run(['git','push','origin',branch], capture_output=True, text=True)
print('git push rc', push_proc.returncode)
# try to create PR with gh if available
gh_path=shutil.which('gh')
if gh_path:
    title=f'Automated snapshot: {ts}'
    body=f'This PR contains an automated status snapshot generated from {source}.'
    try:
        pr=subprocess.run(['gh','pr','create','--title',title,'--body',body,'--base','main','--head',branch], capture_output=True, text=True)
        print('gh pr create rc', pr.returncode)
        print(pr.stdout)
    except Exception as e:
        print('gh pr error', e)
else:
    print('gh CLI not found; branch pushed but PR not created')

# checkout back to main
subprocess.run(['git','checkout','main'])
print('snapshot done', out)
