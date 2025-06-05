import json
from uuid import uuid4
from tqdm import tqdm
from pymilvus import (connections,utility, FieldSchema, CollectionSchema, DataType, Collection)
from pymilvus import Index

def transform_data_to_vector_embedding(text_representations:list,model) -> list:
    vector_embeddings = list(tqdm(
        model.embed(text_representations, batch_size=5),
        total=len(text_representations),
        desc="Text Embedding"
    ))
    print("Done with embedding process...")
    return vector_embeddings


def transform_single_data_to_vector_embedding(text: str, model) -> list:
    print("Generating embedding for single text...")
    vector_embedding = model.embed([text]) [0]# Assuming model.embed returns a list of embeddings
    print("Done with embedding process.")
    return vector_embedding


# def transform_data_to_vector_embedding(text_representation,model) -> list:
#     vector_embeddings =model.embed(text_representation)
#
#     print("Done with embedding process...")
#     return vector_embeddings

def token_length(self, text):
    tokens = self.tokenizer.encode(text)
    return len(tokens)

def create_connection():
    # Connect to Milvus
    print("Create connection ...")
    connections.connect("default", host="localhost", port="19530")
    print("connection created...")

def create_collection_on_empty_db( collection_name = "milvus_llm_example"):
    # create collection if collection dose not exists
    if not utility.has_collection(collection_name):
        print(f"Collection named {collection_name} doesn't exists!")
        collection_name = "milvus_llm_example"
        create_collection(collection_name)
        print(f"Collection named {collection_name} created!")

def create_collection( collection_name) -> Collection:
    create_connection()
    dim=768
    dim_text = 384  # e.g. "all-MiniLM-L6-v2" outputs 384‐dim vectors
    dim_code = 768  # e.g. "jinaai/jina-embeddings-v2-base-code" outputs 768‐dim
    # FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    fields = [ FieldSchema( name="ids", dtype=DataType.VARCHAR, is_primary=True,auto_id=False, max_length=36),
        FieldSchema(name="text_embedding", dtype=DataType.FLOAT_VECTOR, dim=dim_text),
        FieldSchema(name="code_embedding", dtype=DataType.FLOAT_VECTOR, dim=dim_code),
        FieldSchema(name="code_metadata", dtype=DataType.VARCHAR,max_length=65534),
    ]
    schema = CollectionSchema(fields, f" stores both text & code embeddings with code-metadata")

    print(f"Create collection {collection_name}")
    if not utility.has_collection(collection_name):
        collection = Collection(name=collection_name, schema=schema)
    else:
        utility.drop_collection(collection_name)
        collection = Collection(name=collection_name, schema=schema)
        # collection = Collection(name=collection_name)

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




def batch_upload(my_collection, natural_language_embeddings, code_embeddings, code_metadata_lists, batch_size):
    batch_nl_vectors = []
    batch_code_vectors = []
    batch_code_metadata_lists = []
    batch_ids =[]
    # batch_ids= [str(uuid4()) for _ in range(len(code_metadata_lists))]
    for index,code_metadata in tqdm(enumerate(code_metadata_lists)):
        batch_nl_vectors.append(natural_language_embeddings[index])
        batch_code_vectors.append(code_embeddings[index])
        batch_code_metadata_lists.append(json.dumps(code_metadata_lists[index]))
        batch_ids.append(str(uuid4()))
        if len(batch_nl_vectors) >= batch_size:
            insert_data_in_batch(my_collection, batch_ids, batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
            batch_code_vectors=[]
            batch_nl_vectors=[]
            batch_code_metadata_lists=[]
            batch_ids=[]
    if len(batch_nl_vectors) > 0:
        insert_data_in_batch(my_collection, batch_ids, batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
    my_collection.flush()
    #collection.release()


def insert_data_in_batch(collection,ids,natural_language_embeddings, code_embeddings, code_metadata_list):
    insert_data = [ids,
        natural_language_embeddings,  # "text_embedding" FLOAT_VECTOR
        code_embeddings,  # "code_embedding" FLOAT_VECTOR
        code_metadata_list,  # "payload" VARCHAR
    ]
    collection.insert(insert_data)


def batch_encoding_and_upload(my_connection,natural_language_model, code_model, code_metadata_lists,natural_language_representations,code_snippets,batch_size):
    batch_nl_vectors = []
    batch_code_vectors = []
    batch_code_metadata_lists = []
    batch_ids =[]
    # batch_ids= [str(uuid4()) for _ in range(len(code_metadata_lists))]
    for index,code_metadata in tqdm(enumerate(code_metadata_lists)):
        natural_language_embedding=transform_single_data_to_vector_embedding(natural_language_representations[index], natural_language_model)
        code_snippets_vector_embedding = transform_single_data_to_vector_embedding(code_snippets[index],code_model)
        batch_nl_vectors.append(natural_language_embedding)
        batch_code_vectors.append(code_snippets_vector_embedding)
        batch_code_metadata_lists.append(json.dumps(code_metadata))
        batch_ids.append(str(uuid4()))
        if len(batch_nl_vectors) >= batch_size:
            insert_data_in_batch(my_connection,batch_ids,batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
            batch_code_vectors=[]
            batch_nl_vectors=[]
            batch_code_metadata_lists=[]
            batch_ids=[]
    if len(batch_nl_vectors) > 0:
        insert_data_in_batch(my_connection, batch_ids,batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
    insert_data_in_batch(my_connection, batch_ids, batch_nl_vectors, batch_code_vectors, batch_code_metadata_lists)
    my_connection.flush()


