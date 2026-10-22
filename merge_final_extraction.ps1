@'
import sys, json
from pathlib import Path

ast_path = Path('graphify-out/.graphify_ast.json')
sem_path = Path('graphify-out/.graphify_semantic.json')

if not ast_path.exists() or not sem_path.exists():
    print('Error: Missing AST or semantic extraction files.')
    sys.exit(1)

ast = json.loads(ast_path.read_text(encoding="utf-8"))
sem = json.loads(sem_path.read_text(encoding="utf-8"))

# Stamp tier provenance on the semantic side.
for n in sem['nodes']:
    n.setdefault('_origin', 'semantic')
for e in sem['edges']:
    e.setdefault('_origin', 'semantic')

# Merge: AST nodes first, semantic nodes deduplicated by id
seen = {n['id'] for n in ast['nodes']}
merged_nodes = list(ast['nodes'])
for n in sem['nodes']:
    if n['id'] not in seen:
        merged_nodes.append(n)
        seen.add(n['id'])

merged_edges = ast['edges'] + sem['edges']
merged_hyperedges = sem.get('hyperedges', [])
merged = {
    'nodes': merged_nodes,
    'edges': merged_edges,
    'hyperedges': merged_hyperedges,
    'input_tokens': sem.get('input_tokens', 0),
    'output_tokens': sem.get('output_tokens', 0),
}
Path('graphify-out/.graphify_extract.json').write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
print(f'Merged: {len(merged_nodes)} nodes, {len(merged_edges)} edges ({len(ast["nodes"])} AST + {len(sem["nodes"])} semantic)')
'@ | & (Get-Content graphify-out\.graphify_python) -
