from .config.model_config import embeddings
from langchain_chroma import Chroma
from .config.env import CHROMA_DB, COLLECTION_NAME

vs = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=CHROMA_DB,
)

re=vs.delete(ids=[""])
print(re)