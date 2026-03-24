from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from app.config import MODEL_NAME


class Embedder:
    _embedding_function = None

    def __init__(self):
        if self.__class__._embedding_function is None:
            try:
                self.__class__._embedding_function = SentenceTransformerEmbeddingFunction(
                    model_name=MODEL_NAME
                )
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to initialize embedding model '{MODEL_NAME}'. "
                    "If this machine is offline, make sure the model is already cached locally."
                ) from exc

        self.embedding_function = self.__class__._embedding_function

    def get_embedding_function(self):
        return self.embedding_function
