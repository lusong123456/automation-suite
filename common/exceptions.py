"""自定义异常体系。"""


class SuiteError(Exception):
    """所有 automation-suite 异常的基类。"""


class ConfigError(SuiteError):
    """配置缺失或非法时抛出。"""


class AuthenticationError(SuiteError):
    """认证失败或 token 刷新失败时抛出。"""


class ContextExtractionError(SuiteError):
    """jsonpath 提取失败时抛出。"""


class RenderError(SuiteError):
    """模板渲染失败时抛出。"""


class ContractError(SuiteError):
    """契约校验失败时抛出：响应不符合 schema 或 OpenAPI 规范。"""


class MqttError(SuiteError):
    """MQTT 模块异常：连接失败、发布失败等。"""
