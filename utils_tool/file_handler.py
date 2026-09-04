import os
import hashlib

from langchain_community.document_loaders import PyPDFLoader, TextLoader ,JSONLoader
from langchain_core.documents import Document

from utils_tool.logger_handler import logger
from utils_tool.path_tool import get_abs_path


#计算文件的md5
def get_md5_hex(file_path):

    if not os.path.exists(file_path):
        logger.error(f"文件不存在：{file_path}")
        return

    if not os.path.isfile(file_path):
        logger.error(f"{file_path}不是文件")
        return

    md5 = hashlib.md5()

    chunk_size = 4096 #每次读取4096字节,避免大文件占用过多内存
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(chunk_size):
                md5.update(chunk)

        md5_hex = md5.hexdigest()
        return md5_hex
    except Exception as e:
        logger.error(f"计算文件md5出错：{e}")
        return None


def listdir_with_allowed_types(directory, allowed_types:tuple[str]):
    """
    列出目录中指定类型文件的路径

    :param directory: 目录路径
    :param allowed_types: 允许的文件类型列表，例如 ['txt', 'pdf']
    :return: 文件路径列表
    """
    files = []
    abs_directory = get_abs_path(directory)
    if not os.path.isdir(abs_directory):
        logger.error(f"该{directory}不是一个文件夹")
        return []  # 修复：返回空列表而不是 directory
    for file in os.listdir(abs_directory):
        # 修复：构建完整路径，并检查是否为文件
        full_path = get_abs_path(os.path.join(abs_directory, file))
        if os.path.isfile(full_path) and file.endswith(allowed_types):
            files.append(full_path)
    return files  # 修复：返回列表而不是元组

def pdf_loader(file_path:str,password = None) -> list[Document]:
    return PyPDFLoader(file_path,password).load()

def txt_loader(file_path:str) -> list[Document]:
    return TextLoader(file_path,encoding="utf-8").load()

def json_loader(file_path:str) -> list[Document]:
    return JSONLoader(file_path).load()

