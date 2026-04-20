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

    香港电话格式：8位数字，通常 5/6/7/8/9 开头
    例如：5123 4567, 9123 4567
    国际格式：+852 9123 4567, 852-91234567
    """

    PATTERNS = [
        Pattern(
            name="hk_mobile",
            # 基本格式：5/6/7/8/9 开头，共8位
            regex=r"(?<!\d)([5-9]\d{7})(?!\d)",
            score=0.85
        ),
        Pattern(
            name="hk_mobile_spaced",
            # 带空格格式：xxxx xxxx
            regex=r"(?<!\d)([5-9]\d{3})\s(\d{4})(?!\d)",
            score=0.9
        ),
        Pattern(
            name="hk_mobile_hyphen",
            # 连字符格式：xxxx-xxxx
            regex=r"(?<!\d)([5-9]\d{3})-(\d{4})(?!\d)",
            score=0.9
        ),
        Pattern(
            name="hk_intl_with_space",
            # 国际格式带空格：+852 xxxxxxxx
            regex=r"(?<![\d+])(?:\+852)\s?([5-9]\d{7})(?!\d)",
            score=0.95
        ),
        Pattern(
            name="hk_intl_spaced",
            # 国际格式带空格分隔：+852 xxxx xxxx
            regex=r"(?<![\d+])(?:\+852)\s([5-9]\d{3})\s(\d{4})(?!\d)",
            score=0.95
        ),
        Pattern(
        name="hk_intl_hyphen",
            # 国际格式带连字符：+852-xxxx-xxxx
            regex=r"(?<![\d+])(?:\+852)-([5-9]\d{3})-(\d{4})(?!\d)",
            score=0.95
        ),
        Pattern(
            name="hk_code_no_space",
            # 区号无分隔符：852xxxxxxxx
            regex=r"(?<![\d+])852([5-9]\d{7})(?!\d)",
            score=0.85
        ),
        Pattern(
            name="hk_code_hyphen",
            # 区号带连字符：852-xxxx-xxxx 或 852-xxxxxxxx
            regex=r"(?<![\d+])852-([5-9]\d{3})-(\d{4})(?!\d)|852-([5-9]\d{7})(?!\d)",
            score=0.9
        ),
    ]

    CONTEXT = [
        # 简体
        "手机", "电话", "联系电话", "联系方式", "手机号", "移动电话", "电话号码",
        "号码", "致电", "热线",
        # 繁体（香港常用）
        "手機", "手機號", "手機號碼", "電話", "電話號碼", "聯絡電話", "聯絡方式",
        "流動電話", "號碼", "致電", "熱線",
        # 英文（香港常用）
        "mobile", "phone", "telephone", "tel", "contact", "cell", "cellphone",
        "cellular", "number", "call", "hotline", "hk mobile", "hk phone",
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

    括号内校验码：0-9 或 A-Z 字母（校验算法生成的结果）
    有效前缀字母：A-R, T-Z (注意：S 开头的身份证很少见，主要用于特定情况)
    """

    PATTERNS = [
        Pattern(
            name="hk_id_single_letter",
            # 单字母格式：A123456(7) 或 A123456(A)
            # 前缀字母 A-Z，校验码 0-9 或 A-Z
            regex=r"(?<![A-Za-z0-9])([A-Z]\d{6}\([0-9A-Z]\))(?![A-Za-z0-9)])",
            score=0.95
        ),
        Pattern(
            name="hk_id_double_letter",
            # 双字母格式：AB123456(7) 或 AB123456(A)
            # 前缀字母 A-Z，校验码 0-9 或 A-Z
            regex=r"(?<![A-Za-z0-9])([A-Z]{2}\d{6}\([0-9A-Z]\))(?![A-Za-z0-9)])",
            score=0.95
        ),
    ]

    CONTEXT = [
        # 简体
        "身份证", "身份证号", "证件号", "身份号码", "身份证号码", "证件号码",
        "香港身份证", "香港身份证号", "HKID", "HK ID",
        # 繁体（香港常用）
        "身份證", "身份證號碼", "身份證號", "身份證字號", "證件號", "證件號碼",
        "身分證", "身分證字號", "香港身份證", "香港身分證",
        # 英文（香港常用）
        "ID", "ID card", "HKID", "HK ID", "Hong Kong ID", "Hong Kong Identity",
        "identity card", "identification", "ID number", "card number",
        "document", "document no", "document number",
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
    # 参考: https://www.bochk.com/en/popular/hk-surname.html
    HK_SURNAMES = {
        # 十大常见姓氏
        'Wong', 'Chan', 'Lee', 'Cheung', 'Lam', 'Ng', 'Cheng', 'Liu', 'Leung', 'Chow',
        # 其他常见姓氏 (按字母序)
        'Au', 'Chik', 'Chin', 'Chiu', 'Chong', 'Chu', 'Fan', 'Fong', 'Ho', 'Hong',
        'Hung', 'Kam', 'Ko', 'Kwan', 'Kwok', 'Kwong', 'Lau', 'Law', 'Lo', 'Mak',
        'Man', 'Mo', 'Mok', 'Ngai', 'Pang', 'Poon', 'See', 'Sham', 'Shum', 'Sinn',
        'Sit', 'Siu', 'So', 'Suen', 'Sun', 'Sze', 'Szeto', 'Tai', 'Tam', 'Tan',
        'Tang', 'Ting', 'To', 'Tong', 'Tse', 'Tsang', 'Tsui', 'Tsoi', 'Wai', 'Wan',
        'Wang', 'Woo', 'Wu', 'Xiao', 'Xie', 'Xu', 'Yau', 'Yee', 'Yeung', 'Yim',
        'Yin', 'Ying', 'Yip', 'Yiu', 'Yong', 'Yu', 'Yue', 'Yuen', 'Yung',
    }

    # 匹配首字母大写的英文名（2-4 个单词，支持跨行）
    PATTERNS = [
        Pattern(
            name="hk_english_name",
            # 支持空格、制表符或换行符分隔
            regex=r"([A-Z][a-z]+(?:[ \t\n]+[A-Z][a-z]+){1,3})",
            score=0.35
        ),
    ]

    # 上下文关键词
    CONTEXT = [
        # 简体
        "姓名", "名字", "联系人", "客户", "客户姓名", "用户姓名", "持卡人",
        "寄件人", "收件人", "发件人", "发货人", "收货人",
        # 繁体
        "聯絡人", "客戶", "客戶姓名", "用戶姓名", "顧客", "持有人",
        "寄件人", "收件人", "發件人", "發貨人", "收貨人",
        # 英文
        "Name", "name", "NAME",
        "Customer", "customer", "CUSTOMER",
        "Contact", "contact", "CONTACT",
        "Client", "client", "CLIENT",
        "User", "user", "USER",
        "Account Holder", "account holder", "Account holder",
        "Applicant", "applicant", "APPLICANT",
        "Representative", "representative", "REPRESENTATIVE",
        "Contact Person", "contact person", "Contact person",
        "Full Name", "full name", "Full name",
        "Customer Name", "customer name", "Customer name",
        "Client Name", "client name", "Client name",
        "Sender", "sender", "SENDER",
        "Receiver", "receiver", "RECEIVER",
        "Consignor", "consignor", "CONSIGNOR",
        "Consignee", "consignee", "CONSIGNEE",
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

        # 预处理：处理 Name:\nWong 这种情况
        # 在行首位置添加标记，方便后续检测
        lines = text.split('\n')
        processed_lines = []
        for i, line in enumerate(lines):
            processed_lines.append(line)
        processed_text = '\n'.join(processed_lines)

        # 使用正则匹配所有可能的英文名
        for pattern in self.patterns:
            for match in re.finditer(pattern.regex, processed_text):
                start, end = match.start(), match.end()
                matched_text = processed_text[start:end]

                # 检查上下文是否存在于匹配位置前
                # 扩大上下文窗口并处理换行情况
                context_window = processed_text[max(0, start - 100):start]

                # 标准化：替换换行符和制表符为空格，便于匹配
                normalized_context = re.sub(r'[\n\t]+', ' ', context_window).strip()

                has_context = False
                matched_context = None
                for ctx in self.context:
                    # 检查多种变体：原样、带冒号、带空格
                    ctx_variants = [
                        ctx,
                        ctx + ":",
                        ctx + "：",
                    ]
                    for variant in ctx_variants:
                        # 检查标准化后的上下文
                        if variant.lower() in normalized_context.lower():
                            has_context = True
                            matched_context = ctx
                            break
                        # 额外检查：上下文是否在行尾（可能下一行是姓名）
                        if variant.lower() in context_window.lower():
                            has_context = True
                            matched_context = ctx
                            break
                    if has_context:
                        break

                # 检查姓氏是否在常见香港姓氏中
                first_word = matched_text.split()[0] if matched_text.split() else ""
                is_hk_surname = first_word in self.HK_SURNAMES

                # 如果不是香港常见姓氏，降低置信度或跳过
                # 同时检查是否可能是常见西方姓氏
                common_western_surnames = {
                    'Smith', 'Johnson', 'Williams', 'Brown', 'Jones', 'Garcia',
                    'Miller', 'Davis', 'Rodriguez', 'Martinez', 'Hernandez',
                    'Lopez', 'Gonzalez', 'Wilson', 'Anderson', 'Thomas',
                    'Taylor', 'Moore', 'Jackson', 'Martin', 'Lee', 'Walker',
                    'Hall', 'Allen', 'Young', 'King', 'Scott', 'Green',
                    'Adams', 'Baker', 'Nelson', 'Carter', 'Mitchell',
                    'Roberts', 'Turner', 'Phillips', 'Campbell', 'Parker',
                }
                is_western_surname = first_word in common_western_surnames

                # 计算分数
                if has_context:
                    if is_hk_surname:
                        score = 0.85  # 香港姓氏 + 上下文 = 高置信度
                    elif is_western_surname:
                        score = 0.25  # 西方姓氏，可能误判
                    else:
                        score = 0.35  # 不确定的姓氏
                else:
                    # 无上下文，不返回结果
                    continue

                # 如果分数太低，跳过
                if score < 0.5:
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
