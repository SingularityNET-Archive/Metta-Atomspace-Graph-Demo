# Metta Atomspace Graph Demo

This project demonstrates how to create, query, and visualize a small graph using MeTTa and AtomSpace via the Hyperon Python bindings.

## What the Script Does

- **Graph Construction:**  
  The script builds a simple directed graph representing relationships (e.g., "Alice knows Bob") using MeTTa code. It inserts nodes and links into AtomSpace through the Hyperon Python API.

- **AtomSpace Querying:**  
  It attempts to read back the graph structure (OrderedLink atoms) from AtomSpace using several fallback methods, adapting to different Hyperon/MeTTa API versions.

- **Visualization:**  
  The recovered graph triples are converted into a DOT graph and rendered as a PNG image using the `graphviz` Python package.

- **Export:**  
  The script saves the graph visualization as `graph.png` and the recovered triples as `triples.json`.

## Requirements

- Python 3.8+
- [hyperon](https://pypi.org/project/hyperon/) Python package (`pip install hyperon`)
- [graphviz](https://pypi.org/project/graphviz/) Python package (`pip install graphviz`)
- System `graphviz` installed for PNG rendering (`sudo apt install graphviz` on Ubuntu)

## Usage

1. Install dependencies:
   ```
   pip install hyperon graphviz
   sudo apt install graphviz
   ```
2. Run the script:
   ```
   python test.py
   ```
3. View the output files:
   - `graph.png`: Visual representation of the graph
   - `triples.json`: List of recovered triples

## Notes

- The script is robust to changes in the Hyperon/MeTTa API and will fall back to local data if AtomSpace querying fails.
- You can modify the graph structure by editing the `triples` list in the script.