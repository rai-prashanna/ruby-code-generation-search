from openai import AzureOpenAI
import json
import os
from tree_sitter import Language, Parser
import tree_sitter_ruby
RUBY_LANGUAGE = Language(tree_sitter_ruby.language())
parser = Parser()
parser.language = RUBY_LANGUAGE

# Set your Azure OpenAI credentials
endpoint = "https://prashanna-coding-assistant.cognitiveservices.azure.com/"
model_name = "o4-mini"
deployment = "generator-o4-mini"

subscription_key = "AD4Wp37TIK17f1TnZRJj9K3eIkrrrS3Gin1W7RW1vFiLM9sCf438JQQJ99BFACfhMk5XJ3w3AAAAACOGFZgP"
api_version = "2024-12-01-preview"
client = AzureOpenAI(
    api_version=api_version,
    azure_endpoint=endpoint,
    api_key=subscription_key,
)
def extract_classes_and_methods(source):
    """Parse Ruby source and extract all classes and methods."""

    tree = parser.parse(bytes(source, 'utf8'))
    root_node = tree.root_node
    items = []

    def extract(node, lines):
        if node.type == "class":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = source[name_node.start_byte:name_node.end_byte] if name_node else "anonymous"
                start = node.start_point[0]
                end = node.end_point[0]
                code = "\n".join(lines[start:end + 1])
                items.append(('class', name, code, start, end))
        elif node.type == "method":
            name_node = node.child_by_field_name("name")
            if name_node is not None:
                name = source[name_node.start_byte:name_node.end_byte] if name_node else "anonymous"
                start = node.start_point[0]
                end = node.end_point[0]
                code = "\n".join(lines[start:end + 1])
                items.append(('method', name, code, start, end))
            # # name = node.child_by_field_name("name").text.decode()
            # start = node.start_point[0]
            # end = node.end_point[0]
            # code = "\n".join(lines[start:end+1])
            # items.append(('method', name, code, start, end))
        for child in node.children:
            extract(child, lines)

    lines = source.splitlines()
    extract(root_node, lines)
    return items

def generate_docstring(code, item_type, item_name):
    """Call Azure OpenAI to generate a docstring for the given Ruby code."""
    instruction = (
        f"Generate a concise and clear Ruby docstring for the following {item_type} '{item_name}'. "
        f"Only provide the docstring, nothing else."
    )
    messages = [
        {"role": "system", "content": "You are an expert Ruby documentation assistant."},
        {"role": "user", "content": f"{instruction}\n\n{code}"}
    ]

    response = client.chat.completions.create(
        messages=messages,
        max_completion_tokens=100000,
        model=deployment
    )

    return response.choices[0].message.content.strip()

def insert_docstrings(source, items_with_docstrings):
    """Insert generated docstrings into the source code."""
    lines = source.splitlines()
    offset = 0
    for (item_type, item_name, code, start, end, docstring) in items_with_docstrings:
        # Find the line after the definition
        definition_line = lines[start + offset]
        next_line_idx = start + offset + 1
        indent = ' ' * (len(definition_line) - len(definition_line.lstrip()))
        docstring_lines = [indent + l for l in docstring.splitlines()]
        # Insert after the definition line
        lines = lines[:next_line_idx] + docstring_lines + lines[next_line_idx:]
        offset += len(docstring_lines)
    return "\n".join(lines)

def process_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        source = f.read()
    items = extract_classes_and_methods(source)
    items_with_docstrings = []
    for item_type, item_name, code, start, end in items:
        print(f"Generating docstring for {item_type} '{item_name}'...")
        docstring = generate_docstring(code, item_type, item_name)
        items_with_docstrings.append((item_type, item_name, code, start, end, docstring))
        print(f"Docstring for {item_type} '{item_name}':\n{docstring}\n")
    new_source = insert_docstrings(source, items_with_docstrings)
    with open(filepath.replace(".rb", "_with_doc.rb"), "w", encoding="utf-8") as f:
        f.write(new_source)
    print(f"\nDocstrings inserted and saved to {filepath.replace('.rb', '_with_doc.rb')}")

if __name__ == "__main__":
    # import sys
    # if len(sys.argv) < 2:
    #     print("Usage: python generate_docstrings_ruby.py <ruby_file>")
    #     sys.exit(1)
    process_file("/Users/prashanna/PycharmProjects/semantic_ruby_code_base_search/ruby_project/eris/app/controllers/batch_schedules_controller.rb")

# def extract_classes_and_functions(source):
#     """Parse Python source and extract all classes and functions."""
#     tree = ast.parse(source)
#     items = []
#     for node in ast.walk(tree):
#         if isinstance(node, ast.ClassDef):
#             start = node.lineno - 1
#             end = node.body[-1].end_lineno if hasattr(node.body[-1], "end_lineno") else node.body[-1].lineno
#             code = "\n".join(source.splitlines()[start:end])
#             items.append(('class', node.name, code, start, end))
#         elif isinstance(node, ast.FunctionDef):
#             start = node.lineno - 1
#             end = node.body[-1].end_lineno if hasattr(node.body[-1], "end_lineno") else node.body[-1].lineno
#             code = "\n".join(source.splitlines()[start:end])
#             items.append(('function', node.name, code, start, end))
#     return items
#
# def generate_docstring(code, item_type, item_name):
#     """Call Azure OpenAI to generate a docstring for the given code."""
#     instruction = (
#         f"Generate a concise and clear Ruby docstring for the following {item_type} '{item_name}'. "
#         f"Only provide the docstring, nothing else."
#     )
#     messages = [
#         {"role": "system", "content": "You are an expert Python assistant."},
#         {"role": "user", "content": f"{instruction}\n\n{code}"}
#     ]
#
#     response = client.chat.completions.create(
#         messages=messages,
#         max_completion_tokens=100000,
#         model=deployment
#     )
#
#
#     return response.choices[0].message.content
#
# def insert_docstrings(source, items_with_docstrings):
#     """Insert generated docstrings into the source code."""
#     lines = source.splitlines()
#     offset = 0
#     for (item_type, item_name, code, start, end, docstring) in items_with_docstrings:
#         # Find the line after the definition
#         definition_line = lines[start + offset]
#         next_line_idx = start + offset + 1
#         indent = ' ' * (len(definition_line) - len(definition_line.lstrip()))
#         docstring_lines = [f'{indent}"""' + docstring + '"""']
#         # Insert after the function/class definition line
#         lines = lines[:next_line_idx] + docstring_lines + lines[next_line_idx:]
#         offset += len(docstring_lines)
#     return "\n".join(lines)
#
# def process_file(filepath):
#     with open(filepath, 'r', encoding='utf-8') as f:
#         source = f.read()
#     items = extract_classes_and_functions(source)
#     items_with_docstrings = []
#     for item_type, item_name, code, start, end in items:
#         print(f"Generating docstring for {item_type} '{item_name}'...")
#         docstring = generate_docstring(code, item_type, item_name)
#         items_with_docstrings.append((item_type, item_name, "code", start, end, docstring))
#         print(f"Docstring for {item_type} '{item_name}':\n{docstring}\n")
#     new_source = insert_docstrings(source, items_with_docstrings)
#     # Optionally overwrite the original file, or print to console
#     with open(filepath.replace(".py", "_with_doc.py"), "w", encoding="utf-8") as f:
#         f.write(new_source)
#     print(f"\nDocstrings inserted and saved to {filepath.replace('.py', '_with_doc.py')}")
#
# if __name__ == "__main__":
#     # import sys
#     # if len(sys.argv) < 2:
#     #     print("Usage: python generate_docstrings_azure.py <python_file>")
#     #     sys.exit(1)
#     process_file("MilvusDBUtility.rb)