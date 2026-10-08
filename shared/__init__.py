"""跨模块共享层：按职责分组为 auth/ 与 apijson/。

与 common/ 的边界：common 装系统底座（HTTP/auth/config/log/reporting），
任何测试类型都用得到；shared 装跨测试类型复用的业务侧资产
（认证实现、接口契约资产），不是所有测试都用。
"""
