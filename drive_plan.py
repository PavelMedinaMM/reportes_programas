"""Compara los PDF del repo contra drive_sync.json y lista lo que falta subir a Google Drive.
Uso: python3 drive_plan.py            -> imprime JSON con acciones (new / changed / removed)
     python3 drive_plan.py --commit   -> marca como sincronizado el estado actual (correr solo tras subir todo)"""
import json, hashlib, glob, os, sys
os.chdir(os.path.dirname(os.path.abspath(__file__)))
m = json.load(open('drive_sync.json'))
cur = {p: hashlib.sha256(open(p, 'rb').read()).hexdigest() for p in sorted(glob.glob('*/*.pdf'))}
if '--commit' in sys.argv:
    m['synced'] = cur; json.dump(m, open('drive_sync.json', 'w'), indent=1); print('ok', len(cur)); sys.exit()
acts = []
for p, h in cur.items():
    if p not in m['synced'] or m['synced'][p] != h:
        sub, name = p.split('/')
        acts.append({"action": "new" if p not in m['synced'] else "changed", "title": name,
                     "folder": sub, "parentId": m['drive_folders'].get(sub), "sha256": h,
                     "path": os.path.abspath(p)})
for p in m['synced']:
    if p not in cur:
        sub, name = p.split('/'); acts.append({"action": "removed", "title": name, "folder": sub, "parentId": m['drive_folders'].get(sub)})
print(json.dumps(acts, indent=1, ensure_ascii=False))
