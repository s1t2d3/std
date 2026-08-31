from utils.config_handler import prompts_config
from utils.logger_handler import logger
from utils.path_tool import get_abs_path


def load_system_prompt():
    try:
        system_prompt_path = get_abs_path(prompts_config["system_prompt_path"])
    except KeyError as e:
        logger.error("在yaml中没有配置system_prompt_path配置项",str(e))
        raise e

    try:
        return open(system_prompt_path,"r",encoding="utf-8").read()
    except Exception as e:
        print("解析系统提示词文件错误",str(e))
        raise e

def load_rag_prompt():
    try:
        rag_prompt_path = get_abs_path(prompts_config["rag_prompt_path"])
    except KeyError as e:
        logger.error("在yaml中没有配置rag_prompt_path配置项",str(e))
        raise e

    try:
        return open(rag_prompt_path,"r",encoding="utf-8").read()
    except Exception as e:
        print("解析RAG提示词文件错误",str(e))
        raise e

def load_summary_prompt():
    try:
        report_prompt_path = get_abs_path(prompts_config["report_prompt_path"])
    except KeyError as e:
        logger.error("在yaml中没有配置report_prompt_path配置项",str(e))
        raise e

    try:
        return open(report_prompt_path,"r",encoding="utf-8").read()
    except Exception as e:
        print("解析报告提示词文件错误",str(e))
        raise e