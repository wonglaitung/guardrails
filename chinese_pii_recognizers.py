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
import re


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


class HongKongPhoneRecognizer(PatternRecognizer):
    """香港电话识别器（支持简繁体）

    香港电话格式：8位数字，通常 5/6/7/9 开头
    例如：5123 4567, 9123 4567
    """

    PATTERNS = [
        Pattern(
            name="hk_mobile",
            # 香港手机号：5/6/7/8/9 开头，共8位
            regex=r"(?<!\d)([5-9]\d{7})(?!\d)",
            score=0.85
        ),
        Pattern(
            name="hk_mobile_spaced",
            # 带空格格式：xxxx xxxx
            regex=r"(?<!\d)([5-9]\d{3})\s(\d{4})(?!\d)",
            score=0.9
        ),
    ]

    CONTEXT = [
        # 简体
        "手机", "电话", "联系电话", "联系方式", "手机号", "移动电话",
        # 繁体（香港常用）
        "手機", "手機號", "手機號碼", "電話", "電話號碼", "聯絡電話", "聯絡方式", "流動電話",
        # 英文（香港常用）
        "mobile", "phone", "tel", "contact",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "HK_PHONE_NUMBER",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class HongKongIDCardRecognizer(PatternRecognizer):
    """香港身份证识别器（支持简繁体）

    香港身份证格式：
    - 1个英文字母 + 6位数字 + 括号内校验码，如 A123456(7)
    - 2个英文字母 + 6位数字 + 括号内校验码，如 AB123456(7)

    括号内校验码可能是数字或字母 A
    """

    PATTERNS = [
        Pattern(
            name="hk_id_single_letter",
            # 单字母格式：A123456(7) 或 A123456(A)
            regex=r"(?<![A-Za-z0-9])([A-Z]\d{6}\([0-9A]\))(?![A-Za-z0-9)])",
            score=0.95
        ),
        Pattern(
            name="hk_id_double_letter",
            # 双字母格式：AB123456(7) 或 AB123456(A)
            regex=r"(?<![A-Za-z0-9])([A-Z]{2}\d{6}\([0-9A]\))(?![A-Za-z0-9)])",
            score=0.95
        ),
    ]

    CONTEXT = [
        # 简体
        "身份证", "身份证号", "证件号", "身份号码", "身份证号码", "证件号码",
        # 繁体（香港常用）
        "身份證", "身份證號碼", "身份證號", "身份證字號", "證件號", "證件號碼", "HKID", "HKID卡",
        # 英文（香港常用）
        "ID", "ID card", "HKID", "Hong Kong ID", "identity card",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "HK_ID_CARD",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )


class HongKongNameRecognizer(PatternRecognizer):
    """香港英文姓名识别器（基于上下文触发）

    只在上下文关键词（如「姓名：」「Name:」）出现时识别英文姓名。
    格式：首字母大写的英文名，如 "Wong Yan Yee", "Chan Tai Man"
    """

    # 香港常见姓氏（用于验证）
    HK_SURNAMES = {
        'Wong', 'Chan', 'Lee', 'Cheung', 'Lam', 'Ng', 'Cheng', 'Liu', 'Leung', 'Chow',
        'Law', 'Yeung', 'Tang', 'Ho', 'Tsang', 'Poon', 'Mak', 'Chiu', 'Fan', 'Kwok',
        'Lo', 'Chong', 'Lau', 'Fong', 'Yip', 'Chin', 'Yuen', 'Kwan', 'Tam', 'So',
        'Hui', 'Sze', 'To', 'Kwong', 'Chu', 'Kam', 'Mo', 'Yiu', 'Tse', 'Shum',
        'Au', 'Tong', 'Man', 'Chik', 'Pang', 'Sit', 'Mok', 'Ko', 'Wan', 'Hung',
    }

    # 匹配首字母大写的英文名（2-4 个单词，不跨行）
    PATTERNS = [
        Pattern(
            name="hk_english_name",
            regex=r"([A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3})",
            score=0.35
        ),
    ]

    # 上下文关键词
    CONTEXT = [
        # 简体
        "姓名", "名字", "联系人", "客户姓名", "用户姓名", "持卡人",
        # 繁体
        "聯絡人", "客戶姓名", "用戶姓名",
        # 英文
        "Name", "name", "NAME", "Customer", "Contact", "Client",
    ]

    def __init__(
        self,
        patterns: Optional[List[Pattern]] = None,
        context: Optional[List[str]] = None,
        supported_language: str = "en",
        supported_entity: str = "HK_NAME",
    ):
        patterns = patterns or self.PATTERNS
        context = context or self.CONTEXT
        super().__init__(
            supported_entity=supported_entity,
            patterns=patterns,
            context=context,
            supported_language=supported_language,
        )

    def analyze(self, text: str, entities: List[str] = None, nlp_artifacts=None) -> List['RecognizerResult']:
        """重写 analyze 方法，实现自定义的上下文检测"""
        from presidio_analyzer import RecognizerResult
        from presidio_analyzer.analysis_explanation import AnalysisExplanation

        results = []

        # 使用正则匹配所有可能的英文名
        for pattern in self.patterns:
            for match in re.finditer(pattern.regex, text):
                start, end = match.start(), match.end()
                matched_text = text[start:end]

                # 检查上下文是否存在于匹配位置前
                context_window = text[max(0, start - 50):start]

                has_context = False
                matched_context = None
                for ctx in self.context:
                    if ctx.lower() in context_window.lower():
                        has_context = True
                        matched_context = ctx
                        break

                # 检查姓氏是否在常见香港姓氏中
                first_word = matched_text.split()[0]
                is_hk_surname = first_word in self.HK_SURNAMES

                # 计算分数
                if has_context:
                    score = 0.75
                    if is_hk_surname:
                        score = 0.85
                else:
                    # 无上下文，不返回结果
                    continue

                # 创建分析解释
                explanation = AnalysisExplanation(
                    recognizer=self.name,
                    original_score=pattern.score,
                    pattern_name=pattern.name,
                    pattern=pattern.regex,
                    validation_result=None,
                )

                results.append(RecognizerResult(
                    entity_type=self.supported_entities[0],
                    start=start,
                    end=end,
                    score=score,
                    analysis_explanation=explanation,
                ))

        return results


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
    HongKongPhoneRecognizer,
    HongKongIDCardRecognizer,
    HongKongNameRecognizer,
]
