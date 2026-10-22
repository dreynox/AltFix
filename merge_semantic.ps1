@'
import json, glob
from pathlib import Path

# 1. Merge chunks into .graphify_semantic_new.json
chunks = sorted(glob.glob('graphify-out/.graphify_chunk_*.json'))
all_nodes, all_edges, all_hyperedges = [], [], []
total_in, total_out = 0, 0
for c in chunks:
    try:
        content = Path(c).read_text(encoding="utf-8")
        d = json.loads(content)
        if isinstance(d, list):
            # Some agents might return a list of nodes/edges.
            # This is a failure of the prompt, but let's try to handle it.
            # If it's a list, we can't easily determine what it is.
            # For now, we'll just skip it or try to treat it as nodes.
            print(f'Warning: {c} returned a list instead of a dict. Skipping.')
            continue

        all_nodes += d.get('nodes', [])
        all_edges += d.get('edges', [])
        all_hyperedges += d.get('hyperedges', [])
        total_in += d.get('input_tokens', 0)
        total_out += d.get('output_tokens', 0)
    except Exception as e:
        print(f'Warning: failed to parse {c}: {e}')

Path('graphify-out/.graphify_semantic_new.json').write_text(json.dumps({
    'nodes': all_nodes, 'edges': all_edges, 'hyperedges': all_hyperedges,
    'input_tokens': total_in, 'output_tokens': total_out,
}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f'Merged {len(chunks)} chunks into .graphify_semantic_new.json')

# 2. Save to cache (simplified for this run as cache was 0)
Path('graphify-out/.graphify_cached.json').write_text(json.dumps({'nodes':[], 'edges':[], 'hyperedges':[]}, ensure_ascii=False), encoding="utf-8")

# 3. Merge cached + new into .graphify_semantic.json
cached = json.loads(Path('graphify-out/.graphify_cached.json').read_text(encoding="utf-8"))
new = json.loads(Path('graphify-out/.graphify_semantic_new.json').read_text(encoding="utf-8"))

all_nodes = cached['nodes'] + new.get('nodes', [])
all_edges = cached['edges'] + new.get('edges', [])
all_hyperedges = cached.get('hyperedges', []) + new.get('hyperedges', [])
seen = set()
deduped = []
for n in all_nodes:
    if n['id'] not in seen:
        seen.add(n['id'])
        deduped.append(n)

merged = {
    'nodes': deduped,
    'edges': all_edges,
    'hyperedges': all_hyperedges,
    'input_tokens': new.get('input_tokens', 0),
    'output_tokens': new.get('output_tokens', 0),
}
Path('graphify-out/.graphify_semantic.json').write_text(json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8")
print(f'Final semantic merge complete: {len(deduped)} nodes, {len(all_edges)} edges')
'@ | & (Get-Content graphify-out\.graphify_python) -
