import os
from typing import List
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

def load_documents(directory: str) -> List:
    loader = DirectoryLoader(directory, glob="**/*.md")
    documents = loader.load()
    return documents

def split_documents(documents: List, chunk_size: int = 1000, chunk_overlap: int = 200) -> List:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    splits = text_splitter.split_documents(documents)
    return splits

def create_vectorstore(splits: List) -> FAISS:
    embeddings = OpenAIEmbeddings()
    vectorstore = FAISS.from_documents(splits, embeddings)
    return vectorstore

def load_rag_database(directory: str) -> FAISS:
    documents = load_documents(directory)
    splits = split_documents(documents)
    vectorstore = create_vectorstore(splits)
    return vectorstore
