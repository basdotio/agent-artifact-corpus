from langchain_community.document_loaders import PyPDFLoader, DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings

#extract data from the pdfs
def load_pdf_file(data):
    loader = DirectoryLoader(data, 
                             glob="*.pdf",
                             loader_cls = PyPDFLoader
                             )
    documents = loader.load()
    return documents

#Create text chunks from the pdfs
def text_split(extracted_data):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=20,
        length_function=len
    )
    text_chunks = text_splitter.split_documents(extracted_data)
    return text_chunks

#Download the hugging face embeddings
def load_hugging_face_embeddings():
    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"}
    )
    return embeddings