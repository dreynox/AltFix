@'
import json
from graphify.detect import detect
from pathlib import Path
from graphify.paths import out_path
from graphify.watch import _read_build_excludes, _read_build_gitignore
result = detect(Path('.'), extra_excludes=_read_build_excludes(out_path()), gitignore=_read_build_gitignore(out_path()))
Path('graphify-out/.graphify_detect.json').write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
print(f'Detected {result["total_files"]} files')
'@ | & (Get-Content graphify-out\.graphify_python) -
