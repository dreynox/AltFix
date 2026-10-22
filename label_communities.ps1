@'
import sys, json
from graphify.build import build_from_json
from graphify.cluster import score_all
from graphify.analyze import god_nodes, surprising_connections, suggest_questions
from graphify.report import generate
from graphify.export import to_json
from pathlib import Path

extraction = json.loads(Path('graphify-out/.graphify_extract.json').read_text(encoding="utf-8"))
detection  = json.loads(Path('graphify-out/.graphify_detect.json').read_text(encoding="utf-8"))
analysis   = json.loads(Path('graphify-out/.graphify_analysis.json').read_text(encoding="utf-8"))

G = build_from_json(extraction, root=Path('.'), directed=False)
communities = {int(k): v for k, v in analysis['communities'].items()}
cohesion = {int(k): v for k, v in analysis['cohesion'].items()}
tokens = {'input': extraction.get('input_tokens', 0), 'output': extraction.get('output_tokens', 0)}

labels = {
    0: "Patching and Edits",
    1: "Quality Checking",
    2: "Client and Caching",
    3: "Scanning Tests",
    4: "Pipeline Orchestration",
    5: "Image Classification",
    6: "CLI Interface",
    7: "Configuration Management",
    8: "Scanning Logic",
    9: "Eval Fixtures",
    10: "Core Utilities",
    11: "Client Networking",
    12: "Eval Metrics",
    13: "Image Tasks",
    14: "File Iteration",
    15: "Local Vision Client",
    16: "Planning and Results",
    17: "Dashboard UI",
    18: "Revenue Charts",
    19: "Architecture Diagram",
    20: "Project Goals",
    21: "User Growth",
    22: "Landscape Visual",
    23: "Company Logo",
    24: "Deployment Process",
    25: "Production Env",
    26: "Graphify Setup",
    27: "Growth Metrics",
    28: "File Detection",
    29: "Northwind Tools",
    30: "Package Root",
    31: "Quarterly Revenue",
    32: "Smoke Test Dashboard"
}

questions = suggest_questions(G, communities, labels)

report = generate(G, communities, cohesion, labels, analysis['gods'], analysis['surprises'], detection, tokens, '.', suggested_questions=questions)
Path('graphify-out/GRAPH_REPORT.md').write_text(report, encoding="utf-8")
Path('graphify-out/.graphify_labels.json').write_text(json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding="utf-8")
wrote = to_json(G, communities, 'graphify-out/graph.json', community_labels=labels)
print('Report updated with community labels')
'@ | & (Get-Content graphify-out\.graphify_python) -
