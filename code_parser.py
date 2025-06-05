from tree_sitter import Language, Parser
import os

import os
import json
import uuid
from tree_sitter import Language, Parser

# Compile Python grammar
Language.build_library(
  'build/my-languages.so',
  ['tree-sitter-python']
)

PY_LANGUAGE = Language('build/my-languages.so', 'python')
parser = Parser()
parser.set_language(PY_LANGUAGE)

# LSIF utilities
def new_id():
    return str(uuid.uuid4())

def lsif_vertex(kind, **attrs):
    return {
        "id": new_id(),
        "type": "vertex",
        "label": kind,
        **attrs
    }

def lsif_edge(kind, outV, inV):
    return {
        "id": new_id(),
        "type": "edge",
        "label": kind,
        "outV": outV,
        "inV": inV
    }

def walk_tree(node, source_code, path, lsif, doc_id):
    if node.type == 'function_definition':
        name_node = node.child_by_field_name('name')
        name = source_code[name_node.start_byte:name_node.end_byte].decode()
        range_vertex = lsif_vertex("range", start={"line": node.start_point[0], "character": node.start_point[1]},
                                              end={"line": node.end_point[0], "character": node.end_point[1]})
        lsif.append(range_vertex)

        result_set = lsif_vertex("resultSet")
        lsif.append(result_set)

        lsif.append(lsif_edge("next", range_vertex["id"], result_set["id"]))

        hover_result = lsif_vertex("hoverResult", result=f"Function: `{name}` in `{path}`")
        lsif.append(hover_result)
        lsif.append(lsif_edge("textDocument/hover", result_set["id"], hover_result["id"]))

        definition_result = lsif_vertex("definitionResult")
        lsif.append(definition_result)
        lsif.append(lsif_edge("textDocument/definition", result_set["id"], definition_result["id"]))
        lsif.append(lsif_edge("item", definition_result["id"], range_vertex["id"]))

        lsif.append(lsif_edge("contains", doc_id, range_vertex["id"]))

    # recurse
    for child in node.children:
        walk_tree(child, source_code, path, lsif, doc_id)

def parse_file(path):
    with open(path, "rb") as f:
        source_code = f.read()
    tree = parser.parse(source_code)
    return tree, source_code

def lsif_export(code_dir, output_file):
    lsif = []

    meta = lsif_vertex("metaData", version="0.4.3", positionEncoding="utf-16")
    lsif.append(meta)

    for root, dirs, files in os.walk(code_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, code_dir)
                tree, source = parse_file(full_path)

                doc = lsif_vertex("document", languageId="python", uri=f"file://{rel_path}")
                lsif.append(doc)

                # Add basic range nodes
                walk_tree(tree.root_node, source, rel_path, lsif, doc["id"])

    with open(output_file, "w") as f:
        for entry in lsif:
            f.write(json.dumps(entry) + "\n")

# Run the exporter
lsif_export("path/to/your/python/codebase", "out.lsif")

