'''
模型工厂
'''
from abc import ABC, abstractmethod

from langchain_ollama import OllamaEmbeddings
from langchain_openai import ChatOpenAI

from utils_tool.config_handler import rag_config
import os

class BaseModelFactory(ABC):
    @abstractmethod
    def generator(self)  -> []:
        pass

class ChatModel(BaseModelFactory):
    def generator(self):
        model= ChatOpenAI(
            model = rag_config["model"],
            api_key = os.environ.get("DEEPSEEK_API_KEY"),
            base_url = rag_config["base_url"],
            temperature = float(rag_config["temperature"])
        )

        return model

class Embeddings(BaseModelFactory):
    def generator(self) :
        model = OllamaEmbeddings(model = rag_config["embeddings"])

        return model

chat_model = ChatModel().generator()
embed_model = Embeddings().generator()
