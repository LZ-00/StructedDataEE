"""抽取流水线异常。"""


class ExtractionCancelled(Exception):
    """用户或客户端断开连接后中止抽取。"""
