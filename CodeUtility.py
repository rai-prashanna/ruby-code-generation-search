import json
import inflection
import re
from typing import Dict, Any
import torch
from fastembed import TextEmbedding
from tqdm import tqdm

import MilvusDBUtility

torch.set_num_threads(1)

def extract_subclass_and_parent_class(signature: str) -> str:
    match = re.search(r'class\s+(\w+)\s*<\s*([\w:]+)', signature)
    if match:
        subclass = match.group(1)
        parent_class = match.group(2)
        print(f"Subclass: {subclass}")
        print(f"Parent class: {parent_class}")
    else:
        print("No match found.")
    return f"{subclass} is a subclass of {parent_class}"

# Load static code into memory
def load_json_into_memory(file_name:str)->[]:
    print("loading static code into memory...")
    code_metadatas = []
    code_snippets = []
    with open(file_name, "r") as fp:
        for row in fp:
            entry = json.loads(row)
            code_metadatas.append(entry)
            code_snippets.append(entry["context"]["snippet"])
    return code_metadatas,code_snippets

# Convert json into prompt
# it generates text representation by  adding code_type, name, docstring, signature
def generate_prompt_from_code_metadata(chunk: Dict[str, Any]) -> str:
    print("Generating text representations...")
    name = inflection.humanize(inflection.underscore(chunk["name"]))
    signature = inflection.humanize(inflection.underscore(chunk["signature"]))
    base_class_text=""
    docstring_text=""
    if "base_classes" in chunk:
        base_class = ','.join(chunk["base_classes"])
        base_class = inflection.humanize(base_class)
        base_class_text=f" is a subclass of {base_class} "
    if "docstring" in chunk:
        docstring_text = f" that does {chunk['docstring']} "
    context = f" module {chunk['context']['module']} file {chunk['context']['file_name']}"
    if chunk["context"]["struct_name"]:
        struct_name = inflection.humanize(inflection.underscore(chunk["context"]["struct_name"]))
        context = f" defined in struct {struct_name} {context}"
    code_snippet_text=f" has code snippets {chunk['context']['snippet']} "
    text_rep = f"{chunk['code_type']} {name} {base_class_text} {docstring_text} defined as {signature} {context} {code_snippet_text}"
    tokens = re.split(r"\W", text_rep)
    return " ".join(filter(None, tokens))

def transform_data_to_vector_embedding(text_representations:list,model) -> list:
    vector_embeddings = list(tqdm(
        model.embed(text_representations, batch_size=5),
        total=len(text_representations),
        desc="Text Embedding"
    ))
    print("Done with embedding process...")
    return vector_embeddings


code_meta_datas,code_snippets=load_json_into_memory("raw.jsonl")
natural_language_representations = list(map(generate_prompt_from_code_metadata, code_meta_datas))
print("Done with generating text representations...")

print("Generating Natural language embedding ...")
natural_language_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2", threads=0)
natural_language_vector_embedding=transform_data_to_vector_embedding(natural_language_representations, natural_language_model)
print("Generating Code embedding ...")
code_model = TextEmbedding("jinaai/jina-embeddings-v2-base-code", threads=0)
code_snippets_vector_embedding=transform_data_to_vector_embedding(code_snippets, code_model)
print("Create collection or load collection ...")
collection_name="temp"
my_collection=MilvusDBUtility.create_collection(collection_name)
MilvusDBUtility.batch_upload(my_collection, natural_language_vector_embedding, code_snippets_vector_embedding, code_meta_datas, 5)

print("Done...")






