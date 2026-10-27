#!/usr/bin/python3
"""Register the launcher. Pass --autostart to also start at login."""
import argparse
import json
import os
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--autostart',action='store_true')
a=p.parse_args()
root=Path(__file__).resolve().parent
config=Path(os.environ.get('XDG_CONFIG_HOME',Path.home()/'.config'))
data=Path(os.environ.get('XDG_DATA_HOME',Path.home()/'.local/share'))
entry='[Desktop Entry]\nType=Application\nName=FlashFind 闪寻\nComment=双击 Ctrl 快速搜索文件\nExec="'+str(root/'start.sh').replace('\\','\\\\').replace('"','\\"').replace('`','\\`').replace('$','\\$').replace('%','%%')+'"\nIcon='+str(root/'flashfind.svg')+'\nTerminal=false\nCategories=Utility;\n'
(data/'applications').mkdir(parents=True,exist_ok=True)
(data/'applications/flashfind.desktop').write_text(entry)
(config/'flashfind').mkdir(parents=True,exist_ok=True)
c=config/'flashfind/config.json'
if not c.exists(): c.write_text(json.dumps({'roots':[str(Path.home())],'refresh_seconds':600},ensure_ascii=False,indent=2))
if a.autostart:
    (config/'autostart').mkdir(parents=True,exist_ok=True)
    (config/'autostart/flashfind.desktop').write_text(entry.replace('\nIcon=',' --hidden\nIcon='))
print('已添加应用菜单入口：FlashFind 闪寻')
print('配置文件：',c)
