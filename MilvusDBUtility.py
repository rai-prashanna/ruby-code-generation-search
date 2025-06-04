from uuid import uuid4
from pymilvus import Collection
from tqdm import tqdm
from pymilvus import (connections,utility, FieldSchema, CollectionSchema, DataType, Collection)
from pymilvus import Index


def token_length(self, text):
    tokens = self.tokenizer.encode(text)
    return len(tokens)

def create_connection():
    # Connect to Milvus
    connections.connect("default", host="localhost", port="19530")

def create_collection_on_empty_db( collection_name = "milvus_llm_example"):
    # create collection if collection dose not exists
    if not utility.has_collection(collection_name):
        print(f"Collection named {collection_name} doesn't exists!")
        collection_name = "milvus_llm_example"
        create_collection(collection_name)
        print(f"Collection named {collection_name} created!")

def create_collection( collection_name) -> Collection:
    dim=768
    dim_text = 384  # e.g. "all-MiniLM-L6-v2" outputs 384‐dim vectors
    dim_code = 768  # e.g. "jinaai/jina-embeddings-v2-base-code" outputs 768‐dim

    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="text_embedding", dtype=DataType.FLOAT_VECTOR, dim=dim_text),
        FieldSchema(name="code_embedding", dtype=DataType.FLOAT_VECTOR, dim=dim_code),
        FieldSchema(name="code_metadata", dtype=DataType.VARCHAR),
    ]
    schema = CollectionSchema(fields, f" stores both text & code embeddings + payload")

    print(f"Create collection {collection_name}")
    # Connect to collection and show size
    collection = Collection(collection_name)
    print(f"Done with creation of {collection_name} Collection")
    index_params_text = {
        "index_type": "IVF_FLAT",  # or HNSW, etc.
        "metric_type": "IP",  # or "L2"
        "params": {"nlist": 128},
    }
    Index(collection, "text_embedding", index_params_text)

    index_params_code = {
        "index_type": "IVF_FLAT",
        "metric_type": "IP",
        "params": {"nlist": 128},
    }
    Index(collection, "code_embedding", index_params_code)
    collection.load()
    print(collection.num_entities)
    return  collection

# def insert(natural_language_embedding, code_embedding, code_metadata):


def insert_data_in_batch(collection,natural_language_embeddings, code_embeddings, code_metadata_list):
    insert_data = [
        natural_language_embeddings,  # "text_embedding" FLOAT_VECTOR
        code_embeddings,  # "code_embedding" FLOAT_VECTOR
        code_metadata_list,  # "payload" VARCHAR
    ]
    collection.insert(insert_data)

def batch_upload(collection,natural_language_embeddings, code_embeddings, code_metadata_lists,batch_size):
    batch_nl_vectors = []
    batch_code_vectors = []
    batch_code_metadata_lists = []
    for natural_language, code_snippet, code_metadata in tqdm(zip(natural_language_embeddings, code_embeddings, code_metadata_lists)):
        print("natural")
        batch_nl_vectors.extend(natural_language)
        batch_code_vectors.extend(code_snippet)
        batch_code_metadata_lists.extend(code_metadata)
        if len(batch_nl_vectors) >= batch_size:
            insert_data_in_batch(collection,batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
            batch_code_vectors=[]
            batch_nl_vectors=[]
            batch_code_metadata_lists=[]
    if len(batch_nl_vectors) > 0:
        insert_data_in_batch(collection, batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
    collection.flush()


def upload_batch(self, texts, metadatas):
    ids = [str(uuid4()) for _ in range(len(texts))]
    embeddings = self.embedder.encode(texts)
    self.collection.insert([ids, embeddings, metadatas])

