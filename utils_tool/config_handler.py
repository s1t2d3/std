

import yaml

from Utils.path_tool import get_abs_path


def load_rag_config(config_path = get_abs_path("config/rag.yaml"),encoding = "utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,yaml.FullLoader)

def load_chrom_config(config_path = get_abs_path("config/chrom.yaml"),encoding = "utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,yaml.FullLoader)

def load_prompts_config(config_path = get_abs_path("config/prompts.yaml"),encoding = "utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,yaml.FullLoader)

def load_agent_config(config_path = get_abs_path("config/agent.yaml"),encoding = "utf-8"):
    with open(config_path,"r",encoding=encoding) as f:
        return yaml.load(f,yaml.FullLoader)

rag_config = load_rag_config()
chrom_config = load_chrom_config()
prompts_config = load_prompts_config()
agent_config = load_agent_config()

if __name__ == "__main__":
    print(rag_config["chat_model"])
