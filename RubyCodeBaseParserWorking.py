import json
import os
from tree_sitter import Language, Parser
import tree_sitter_ruby

RUBY_LANGUAGE = Language(tree_sitter_ruby.language())

parser = Parser()
parser.language = RUBY_LANGUAGE

def get_leading_comments(code_lines, start_line):
    comments = []
    idx = start_line - 2
    while idx >= 0:
        line = code_lines[idx].strip()
        if line.startswith("#"):
            # Ignore magic comment line
            if line.lstrip("#").strip() == "frozen_string_literal: true":
                idx -= 1
                continue
            comments.insert(0, line.lstrip("#").strip())
        elif line == "":
            idx -= 1
            continue
        else:
            break
        idx -= 1
    return "\n".join(comments)

def extract_signature(code):
    sig = code.strip().split("\n")[0]
    return sig.replace('\n', ' ').strip()

def extract_base_classes(class_node, code):
    superclass_node = class_node.child_by_field_name("superclass")
    if not superclass_node:
        return []
    superclass_text = code[superclass_node.start_byte:superclass_node.end_byte]
    # Split by ::, remove whitespace
    return [part.strip() for part in superclass_text.split("::")]

def parse_ruby_file(filepath: str, parser: Parser):
    with open(filepath, 'r', encoding='utf-8') as f:
        code = f.read()
    code_lines = code.splitlines()

    tree = parser.parse(bytes(code, "utf8"))
    root = tree.root_node

    results = []

    def walk(node, parent_class=None):
        for child in node.children:
            if child.type in ("method", "class", "module"):
                start_line = child.start_point[0] + 1
                end_line = child.end_point[0] + 1
                name_node = child.child_by_field_name("name")
                name = code[name_node.start_byte:name_node.end_byte] if name_node else "anonymous"

                snippet = code[child.start_byte:child.end_byte]
                docstring = get_leading_comments(code_lines, child.start_point[0] + 1)
                code_type = {
                    "method": "Function",
                    "class": "Class",
                    "module": "Module"
                }[child.type]

                entry = {
                    "name": name,
                    "signature": extract_signature(snippet),
                    "code_type": code_type,
                    "docstring": docstring,
                    "line": start_line,
                    "line_from": start_line,
                    "line_to": end_line,
                    "context": {
                        "module": os.path.basename(os.path.dirname(filepath)),
                        "file_path": filepath,
                        "file_name": os.path.basename(filepath),
                        "struct_name": parent_class if code_type == "Function" else None,
                        "snippet": snippet.strip()
                    }
                }
                if child.type == "class":
                    entry["base_classes"] = extract_base_classes(child, code)
                results.append(entry)
                # If this is a class, pass class name down
                class_name = name if child.type == "class" else parent_class
                walk(child, parent_class=class_name)
            else:
                walk(child, parent_class=parent_class)

    walk(root)
    return results

def list_ruby_files(directory: str):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.rb'):
                yield os.path.join(root, file)

def main(codebase_path: str, output_file: str):
    with open(output_file, 'w', encoding='utf-8') as out_f:
        for filepath in list_ruby_files(codebase_path):
            print(f"📄 Parsing {filepath}")
            results = parse_ruby_file(filepath, parser)
            for entry in results:
                out_f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    print(f"\n✅ Done! Output written to {output_file}")

main("/Users/prashanna/PycharmProjects/semantic_ruby_code_base_search/ruby_project/eris/app/controllers", "cytiva.jsonl")
print("End")