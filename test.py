"""
MeTTa + AtomSpace graph demo + visualization

Save as: metta_atomspace_graph_demo.py
Run:    python metta_atomspace_graph_demo.py

What it does:
- Creates a small graph in AtomSpace using MeTTa code via the Hyperon Python bindings
- Attempts to read back OrderedLink atoms from the AtomSpace (best-effort; Hyperon API names differ between releases)
- Builds a DOT graph from the recovered triples and renders it as PNG using graphviz

Requirements:
- Python 3.8+
- hyperon package (pip install hyperon) or a local build of Hyperon with Python bindings
- graphviz Python package (pip install graphviz)
- system `graphviz` installed (for rendering to PNG) or use viewable DOT source

Notes on portability:
- Hyperon/MeTTa Python API has changed across releases. This script tries two ways to read atoms back:
   1) If MeTTa exposes a `.space` or `.get_space()` with `get_atoms_by_type`, it will use that (preferred).
   2) Otherwise it falls back to parsing pattern-match results from MeTTa `find` output, or — as a last resort — uses the triples the script created locally.
- If the script can't access AtomSpace programmatically in your installation, you'll still get a correct DOT export based on the triples that were inserted.

"""

from typing import List, Tuple
import sys
import json

try:
    from hyperon import MeTTa
except Exception as e:
    print("ERROR: failed to import hyperon. Install the package with: pip install hyperon\n", e)
    sys.exit(1)

try:
    from graphviz import Digraph
except Exception as e:
    print("ERROR: install the graphviz Python package: pip install graphviz\n", e)
    sys.exit(1)

# --- 1) Create a MeTTa interpreter and build a small graph ---
metta = MeTTa()

# We'll build a simple 'knows' graph: Alice -> Bob, Bob -> Charlie, Alice -> Charlie
triples = [
    ("Alice", "knows", "Bob"),
    ("Bob",   "knows", "Charlie"),
    ("Alice", "knows", "Charlie"),
]

# MeTTa snippet to add Nodes and OrderedLinks. We also record the triples in Python (above).
metta_snippets = []
for s, r, o in triples:
    # Use Node atoms for s, r, o and an OrderedLink (subject relation object)
    snippet = f"(add-atom (Node \"{s}\"))\n(add-atom (Node \"{r}\"))\n(add-atom (Node \"{o}\"))\n(add-atom (OrderedLink (Node \"{s}\") (Node \"{r}\") (Node \"{o}\")))\n"
    metta_snippets.append(snippet)

full_code = "\n".join(metta_snippets)
print('\n--- Running MeTTa code to insert atoms into AtomSpace ---')
res = metta.run(full_code)
print('MeTTa insert result (raw):', res)

# --- 2) Try to read back OrderedLink atoms from the AtomSpace ---
# We'll attempt multiple fallbacks depending on what the Hyperon binding exposes.
retrieved_triples: List[Tuple[str, str, str]] = []

# Fallback A: If the metta object exposes a 'get_space' or 'space' attribute with get_atoms_by_type
space = None
if hasattr(metta, 'get_space'):
    try:
        space = metta.get_space()
        print('Using metta.get_space() to access AtomSpace')
    except Exception:
        space = None
elif hasattr(metta, 'space'):
    space = getattr(metta, 'space')
    print('Using metta.space to access AtomSpace')

if space is not None:
    # Try a few reasonable method names for listing atoms by type
    get_atoms = None
    for name in ('get_atoms_by_type', 'atoms_by_type', 'get_atoms'):
        if hasattr(space, name):
            get_atoms = getattr(space, name)
            break

    if get_atoms is not None:
        try:
            ordered_links = get_atoms('OrderedLink')
            print(f'Found {len(ordered_links)} OrderedLink atoms via space API')
            # Try to extract elements from each OrderedLink
            for al in ordered_links:
                try:
                    # common accessor patterns vary; try a few
                    if hasattr(al, 'elements'):
                        elems = al.elements()
                    elif hasattr(al, 'get_elements'):
                        elems = al.get_elements()
                    elif hasattr(al, 'args'):
                        elems = al.args
                    else:
                        elems = list(al)

                    # elems may be Atom objects; try to get their string form
                    parts = []
                    for e in elems:
                        # If it's a Node or string-like, try str(e) or e.to_string()
                        if hasattr(e, 'to_string'):
                            parts.append(e.to_string())
                        else:
                            parts.append(str(e))

                    # Expecting [subject, relation, object]
                    if len(parts) >= 3:
                        retrieved_triples.append((parts[0].strip('"'), parts[1].strip('"'), parts[2].strip('"')))
                except Exception:
                    # ignore atom if we can't parse it here
                    continue
        except Exception as e:
            print('space.get_atoms_by_type failed:', e)

# Fallback B: Use MeTTa pattern find to return matching OrderedLinks
if not retrieved_triples:
    try:
        print('Attempting MeTTa pattern find for OrderedLink atoms')
        # pattern style: (find (OrderedLink $s $r $o))  -- depending on MeTTa stdlib
        find_result = metta.run('(find (OrderedLink $s $r $o))')
        print('Raw find result:', find_result)
        # The format of find_result depends on Hyperon version. We'll try to interpret common formats.
        # If find_result is a list-like of match dicts, parse them.
        try:
            # Some versions return Python lists or objects convertible to list
            for item in list(find_result):
                # item might be a tuple/list like (s, r, o) or a dict
                if isinstance(item, (list, tuple)) and len(item) >= 3:
                    retrieved_triples.append((str(item[0]).strip('"'), str(item[1]).strip('"'), str(item[2]).strip('"')))
                elif isinstance(item, dict):
                    s = item.get('$s') or item.get('s') or item.get('s')
                    r = item.get('$r') or item.get('r')
                    o = item.get('$o') or item.get('o')
                    if s and r and o:
                        retrieved_triples.append((str(s).strip('"'), str(r).strip('"'), str(o).strip('"')))
        except Exception:
            # If we can't iterate, try to stringify and parse heuristically
            text = str(find_result)
            # A very rough parse: look for sequences like (Node "Alice") etc. This is fragile.
            import re
            nodes = re.findall(r'OrderedLink\s*\((?:Node\s*)?"?([^\)\s"]+)"?\)\s*\((?:Node\s*)?"?([^\)\s"]+)"?\)\s*\((?:Node\s*)?"?([^\)\s"]+)"?\)', text)
            for t in nodes:
                if len(t) == 3:
                    retrieved_triples.append(t)
    except Exception as e:
        print('Pattern find failed or returned nothing:', e)

# Final fallback: use the triple list we constructed locally
if not retrieved_triples:
    print('No triples recovered from AtomSpace; falling back to local triple list')
    retrieved_triples = triples.copy()

print('\nRecovered triples:')
for t in retrieved_triples:
    print(t)

# --- 3) Visualize with graphviz ---
print('\n--- Building graphviz DOT graph and rendering to file graph.png ---')
g = Digraph('AtomSpaceGraph', format='png')

# Add nodes with simple labels
nodes = set()
for s, r, o in retrieved_triples:
    nodes.add(s)
    nodes.add(o)

for n in nodes:
    g.node(n, label=n)

# Add edges with relation as edge label
for s, r, o in retrieved_triples:
    # Graphviz doesn't natively support labeling edges with complex atoms cleanly; we use the relation string
    g.edge(s, o, label=r)

out_path = 'graph'
try:
    g.render(out_path, cleanup=True)
    print(f'Wrote graph to {out_path}.png')
except Exception as e:
    print('Graphviz render failed — printing DOT source instead:\n', e)
    print('\nDOT source:\n')
    print(g.source)

# Optionally, save the triples to a JSON file for inspection
with open('triples.json', 'w') as f:
    json.dump(retrieved_triples, f, indent=2)

print('\nDone. Files produced:')
print('- graph.png (if graphviz rendering succeeded)')
print('- triples.json (recovered triples)')
print('\nIf you want a different layout or export format, change the graphviz.format value (e.g. svg) or open graph.png in your image viewer.')
