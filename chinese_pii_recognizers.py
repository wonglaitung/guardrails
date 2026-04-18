"""
中国 PII 识别器模块

包含针对中国特定 PII 类型的识别器：
- 手机号
- 身份证号
- 银行卡号
- 护照号
- 统一社会信用代码
- 车牌号
- 邮箱（改进版）
- IP地址（中文上下文支持）

支持简体中文和繁体中文
"""

from presidio_analyzer import Pattern, PatternRecognizer
from typing import List, Optional


class ChinaMobilePhoneRecognizer(PatternRecognizer):
    """中国手机号识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_mobile",
            regex=r"(?<!\d)(1[3-9]\d{9})(?!\d)",
            score=0.95
        )
    ]

    # 简体 + 繁体上下文关键词
    CONTEXT = [
        # 简体
        "手机", "电话", "联系电话", "联系方式", "手机号", "移动电话", "电话号码", "联系手机",
        # 繁体
        "手機", "手機號", "手機號碼", "電話", "電話號碼", "聯絡電話", "聯絡方式", "行動電話",
        # 英文
        "mobile", "phone"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_PHONE_NUMBER",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class ChinaIDCardRecognizer(PatternRecognizer):
    """中国身份证号识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_id_18",
            regex=r"(?<!\d)([1-9]\d{5}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx])(?!\d)",
            score=0.95
        ),
        Pattern(
            name="china_id_15",
            regex=r"(?<!\d)([1-9]\d{5}\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3})(?!\d)",
            score=0.85
        )
    ]

    CONTEXT = [
        # 简体
        "身份证", "身份证号", "证件号", "身份号码", "身份证号码", "证件号码", "公民身份号码",
        # 繁体（台湾用法）
        "身分證", "身分證字號", "身分證號碼", "證件號", "證件號碼", "身份證", "身份證號",
        # 英文
        "ID", "ID number"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_ID_CARD",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class ChinaBankCardRecognizer(PatternRecognizer):
    """中国银行卡号识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_bank_card",
            regex=r"(?<!\d)(\d{16,19})(?!\d)",
            score=0.6
        )
    ]

    CONTEXT = [
        # 简体
        "银行卡", "银行卡号", "卡号", "账号", "账户", "储蓄卡", "信用卡", "借记卡",
        # 繁体
        "銀行卡", "銀行卡號", "銀行帳號", "卡號", "帳號", "帳戶", "儲蓄卡", "信用卡", "借記卡",
        # 英文
        "card", "bank card", "account"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_BANK_CARD",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class ChinaPassportRecognizer(PatternRecognizer):
    """中国护照号识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_passport",
            regex=r"(?<![A-Za-z0-9])([EG]\d{8})(?![A-Za-z0-9])",
            score=0.9
        )
    ]

    CONTEXT = [
        # 简体
        "护照", "护照号", "护照号码",
        # 繁体
        "護照", "護照號", "護照號碼",
        # 英文
        "passport"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_PASSPORT",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class ChinaSocialCreditCodeRecognizer(PatternRecognizer):
    """统一社会信用代码识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_social_credit",
            regex=r"(?<![A-Za-z0-9])([0-9A-HJ-NPQRTUWXY]{2}\d{6}[0-9A-HJ-NPQRTUWXY]{10})(?![A-Za-z0-9])",
            score=0.9
        )
    ]

    CONTEXT = [
        # 简体
        "统一社会信用代码", "社会信用代码", "信用代码", "企业代码", "营业执照号",
        # 繁体
        "統一社會信用代碼", "社會信用代碼", "信用代碼", "企業代碼", "營業執照號",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_SOCIAL_CREDIT_CODE",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class ChinaLicensePlateRecognizer(PatternRecognizer):
    """中国车牌号识别器（支持简繁体）"""

    PATTERNS = [
        Pattern(
            name="china_license_plate",
            regex=r"(?<![京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领A-Z])([京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-HJ-NP-Z0-9]{4,5}[A-HJ-NP-Z0-9学警港澳])(?![A-HJ-NP-Z0-9])",
            score=0.9
        )
    ]

    CONTEXT = [
        # 简体
        "车牌", "车牌号", "车牌号码", "车辆号牌",
        # 繁体
        "車牌", "車牌號", "車牌號碼", "車輛號牌",
        # 英文
        "license plate", "plate"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "CN_LICENSE_PLATE",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class EmailRecognizerCN(PatternRecognizer):
    """邮箱识别器（支持简繁体中文上下文）"""

    PATTERNS = [
        Pattern(
            name="email_pattern_cn",
            regex=r"(?<![a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})",
            score=0.95
        )
    ]

    CONTEXT = [
        # 简体
        "邮箱", "邮件", "电子邮件", "邮箱地址",
        # 繁体
        "信箱", "郵箱", "郵件", "電子郵件", "郵箱地址", "電子信箱", "聯絡信箱",
        # 英文
        "email", "Email", "E-mail", "mail"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "EMAIL_ADDRESS",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class IpRecognizerCN(PatternRecognizer):
    """IP 地址识别器（支持简繁体中文上下文）"""

    PATTERNS = [
        Pattern(
            name="ip_pattern_cn",
            regex=r"(?<![0-9.])(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)(?![0-9.])",
            score=0.8
        )
    ]

    CONTEXT = [
        # 简体
        "IP", "IP地址", "ip", "地址", "服务器", "服务器地址", "网络地址",
        # 繁体
        "IP位址", "伺服器", "伺服器位址", "網路位址",
        # 英文
        "IP address", "server"
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "IP_ADDRESS",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


# 导出所有识别器
CHINA_PII_RECOGNIZERS = [
    ChinaMobilePhoneRecognizer,
    ChinaIDCardRecognizer,
    ChinaBankCardRecognizer,
    ChinaPassportRecognizer,
    ChinaSocialCreditCodeRecognizer,
    ChinaLicensePlateRecognizer,
    EmailRecognizerCN,
    IpRecognizerCN,
]
