import json
import inflection
import re
from typing import Dict, Any
import torch
from fastembed import TextEmbedding
from tqdm import tqdm
import MilvusDBUtility
from dotenv import load_dotenv
# Add Azure OpenAI package
from openai import AzureOpenAI
import os
torch.set_num_threads(1)

azure_oai_endpoint = os.getenv("AZURE_OAI_ENDPOINT")
azure_oai_key = os.getenv("AZURE_OAI_KEY")
azure_oai_deployment = os.getenv("AZURE_OAI_DEPLOYMENT")
api_version = "2024-12-01-preview"
model = azure_oai_deployment
_client = None  # Module-level variable to store the client

# parses Gemfile and removes blank/empty line spaces and comments
def parse_gemfile(lockfile_path):
    with open(lockfile_path, "r") as f:
        lines = f.readlines()

    # Remove comments and blank lines
    lines = [line.split('#')[0].strip() for line in lines]
    lines = [line for line in lines if line]  # remove empty lines
    return lines



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

def get_client_from_azure_open_ai_foundry() -> AzureOpenAI:
    global _client
    if _client is None:
        load_dotenv()
        _client = AzureOpenAI(
            azure_endpoint=azure_oai_endpoint,
            api_key=azure_oai_key,
            api_version=api_version
        )
        print(f"Successfully connected with azure ai model: {azure_oai_endpoint}")
    return _client

def transform_query_to_vector_embedding_using_azure_open_ai_model(query: str) -> list:
    client = get_client_from_azure_open_ai_foundry()
    nl_vector_response = client.embeddings.create(
        input=query,
        model=azure_oai_deployment
    )
    print("Done with embedding process and got raw response...")
    vectors = []
    for item in nl_vector_response.data:
        vectors.append(item.embedding)
    print("Done with extracting vectors...")
    return vectors

def transform_data_to_vector_embedding_using_azure_open_ai_model(datas:list) -> list:
    client=get_client_from_azure_open_ai_foundry()
    nl_vector_response = client.embeddings.create(
        input=natural_language_representations,
        model=azure_oai_deployment
    )
    print("Done with embedding process and got raw response...")
    vectors = []
    for item in nl_vector_response.data:
        vectors.append(item.embedding)
    print("Done with extracting vectors...")
    return vectors

# code_meta_datas,code_snippets=load_json_into_memory("raw.jsonl")
# natural_language_representations = list(tqdm(map(generate_prompt_from_code_metadata, code_meta_datas)))
# # natural_language_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2", threads=0)
# load_dotenv()
# azure_oai_endpoint = os.getenv("AZURE_OAI_ENDPOINT")
# azure_oai_key = os.getenv("AZURE_OAI_KEY")
# azure_oai_deployment = os.getenv("AZURE_OAI_DEPLOYMENT")
# api_version = "2024-12-01-preview"
#
# client = AzureOpenAI(
#         azure_endpoint=azure_oai_endpoint,
#         api_key=azure_oai_key,
#         api_version=api_version
#     )
# model = azure_oai_deployment
#
# nl_vector_response =client.embeddings.create(
#     input=natural_language_representations,
#     model=azure_oai_deployment
# )
#
# nl_vectors=[]
# for item in nl_vector_response.data:
#     length = len(item.embedding)
#     nl_vectors.append(item.embedding)
#     print(
#         f"data[{item.index}]: length={length}, "
#         f"[{item.embedding[0]}, {item.embedding[1]}, "
#         f"..., {item.embedding[length-2]}, {item.embedding[length-1]}]"
#     )
# # natural_language_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2", threads=0)
#
# code_model = TextEmbedding("jinaai/jina-embeddings-v2-base-code", threads=0)

# print("Done with generating text representations...")
# print("Generating Natural language embedding ...")
# natural_language_vector_embedding=transform_data_to_vector_embedding(natural_language_representations, natural_language_model)
# print("Generating Code embedding ...")
# code_snippets_vector_embedding=transform_data_to_vector_embedding(code_snippets, code_model)
# print("Create collection or load collection ...")
# collection_name="azureEmbedding"
# my_collection=MilvusDBUtility.create_collection(collection_name)
# MilvusDBUtility.batch_upload(my_collection, natural_language_vector_embedding, code_snippets_vector_embedding, code_meta_datas, 5)
# # my_collection.release()
#
#
# # natural_language_model = TextEmbedding("sentence-transformers/all-MiniLM-L6-v2", threads=0)
# # code_model = TextEmbedding("jinaai/jina-embeddings-v2-base-code", threads=0)
# print("Create collection or load collection ...")
# collection_name="temp"
# my_collection=MilvusDBUtility.load_connection(collection_name)
# # MilvusDBUtility.batch_upload(my_collection, natural_language_vector_embedding, code_snippets_vector_embedding, code_meta_datas, 5)
# query = "How to create scheduling works?"
# natural_language_query_vec = MilvusDBUtility.transform_query_to_vector_embedding(query, natural_language_model)
# code_query_vec = MilvusDBUtility.transform_query_to_vector_embedding(query, code_model)
#
# natural_lang_results = my_collection.search(
#     data=natural_language_query_vec,
#     anns_field="text_embedding",
#     param={"metric_type": "IP", "params": {"nprobe": 10}},
#     limit=5,
#     output_fields=["code_metadata"],  # you’ll get back the serialized structure JSON
# )
#
# sorted_natural_lang_results = sorted(natural_lang_results[0], key=lambda x: x.score, reverse=True)
#
# code_results = my_collection.search(
#     data=code_query_vec,
#     anns_field="code_embedding",
#     param={"metric_type": "IP", "params": {"nprobe": 10}},
#     limit=5,
#     output_fields=["code_metadata"],  # you’ll get back the serialized structure JSON
# )
#
# sorted_code_results = sorted(code_results[0], key=lambda x: x.score, reverse=True)
#
# print("search result using natural_language model ")
#
# for hit in sorted_natural_lang_results:
#     print(f"Score: {hit.score:.4f}")
#     print("Payload:", json.loads(hit.entity.get("code_metadata")))
#     print("─" * 40)
#
# print(".............")
#
# print("search result using code model")
#
# for hit in sorted_code_results:
#     print(f"Score: {hit.score:.4f}")
#     print("Payload:", json.loads(hit.entity.get("code_metadata")))
#     print("─" * 40)
# my_collection.release()
# print("Done...")






