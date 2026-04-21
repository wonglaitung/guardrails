"""
中文 PII Guardrail - 主模块

提供完整的中文敏感信息检测与脱敏功能。
支持中国特有的 PII 类型：手机号、身份证、银行卡、护照、车牌等。
"""

import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from presidio_analyzer import AnalyzerEngine, RecognizerResult
from presidio_anonymizer import AnonymizerEngine

from chinese_pii_recognizers import (
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
)
from chinese_name_recognizer import ChineseNameRecognizer, NameMatch


@dataclass
class PIIEntity:
    """PII 实体信息"""
    entity_type: str
    text: str
    start: int
    end: int
    score: float

    def __repr__(self):
        return f"PIIEntity({self.entity_type}: '{self.text}', score={self.score:.2f})"


class ChinesePIIGuardrail:
    """
    中文 PII 安全护栏

    使用方法:
        guardrail = ChinesePIIGuardrail()

        # 检测 PII
        entities = guardrail.detect("我的手机号是13812345678")

        # 脱敏处理
        safe_text = guardrail.redact("我的身份证号是110101199001011234")
        # 输出: "我的身份证号是<身份证号>"

        # 完整检查（检测+脱敏）
        result = guardrail.check("联系人：张三，电话：13912345678")
    """

    # 脱敏占位符映射（支持简繁体）
    DEFAULT_PLACEHOLDERS = {
        "CN_PHONE_NUMBER": "<手机号>",
        "CN_ID_CARD": "<身份证号>",
        "CN_BANK_CARD": "<银行卡号>",
        "CN_PASSPORT": "<护照号>",
        "CN_SOCIAL_CREDIT_CODE": "<统一社会信用代码>",
        "CN_LICENSE_PLATE": "<车牌号>",
        "EMAIL_ADDRESS": "<邮箱>",
        "PERSON": "<姓名>",
        "LOCATION": "<地址>",
        "IP_ADDRESS": "<IP地址>",
        "URL": "<网址>",
        "PHONE_NUMBER": "<电话>",
        "CREDIT_CARD": "<信用卡号>",
        "HK_PHONE_NUMBER": "<香港电话>",
        "HK_ID_CARD": "<香港身份证>",
        "HK_NAME": "<香港姓名>",
    }

    # 繁体中文占位符
    TRADITIONAL_PLACEHOLDERS = {
        "CN_PHONE_NUMBER": "<手機號>",
        "CN_ID_CARD": "<身分證字號>",
        "CN_BANK_CARD": "<銀行卡號>",
        "CN_PASSPORT": "<護照號>",
        "CN_SOCIAL_CREDIT_CODE": "<統一社會信用代碼>",
        "CN_LICENSE_PLATE": "<車牌號>",
        "EMAIL_ADDRESS": "<信箱>",
        "PERSON": "<姓名>",
        "LOCATION": "<地址>",
        "IP_ADDRESS": "<IP位址>",
        "URL": "<網址>",
        "PHONE_NUMBER": "<電話>",
        "CREDIT_CARD": "<信用卡號>",
        "HK_PHONE_NUMBER": "<香港電話>",
        "HK_ID_CARD": "<香港身份證>",
        "HK_NAME": "<香港姓名>",
    }

    def __init__(
        self,
        placeholders: Optional[Dict[str, str]] = None,
        min_score: float = 0.5,
        script_type: str = "simplified",
        enable_name_recognition: bool = True,
    ):
        """
        初始化中文 PII Guardrail

        Args:
            placeholders: 自定义占位符映射
            min_score: 最小置信度阈值，低于此值的实体将被忽略
            script_type: 字体类型，"simplified"（简体）或 "traditional"（繁体）
            enable_name_recognition: 是否启用中文姓名识别
        """
        # 配置 Presidio：使用轻量级英文模型，避免运行时下载大模型
        from presidio_analyzer import AnalyzerEngine, RecognizerRegistry
        from presidio_analyzer.nlp_engine import NlpEngineProvider
        registry = RecognizerRegistry()
        nlp_config = {"nlp_engine_name": "spacy", "models": [{"lang_code": "en", "model_name": "en_core_web_sm"}]}
        nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()
        self.analyzer = AnalyzerEngine(registry=registry, nlp_engine=nlp_engine)
        self.anonymizer = AnonymizerEngine()
        self.min_score = min_score
        self.script_type = script_type
        self.enable_name_recognition = enable_name_recognition

        # 根据字体类型选择占位符
        base_placeholders = (
            self.TRADITIONAL_PLACEHOLDERS
            if script_type == "traditional"
            else self.DEFAULT_PLACEHOLDERS
        )
        self.placeholders = {**base_placeholders, **(placeholders or {})}

        # 初始化中文姓名识别器
        self.name_recognizer = None
        if enable_name_recognition:
            try:
                self.name_recognizer = ChineseNameRecognizer(use_spacy=True)
            except Exception:
                pass

        # 注册中国 PII 识别器
        self._register_china_recognizers()

    def _register_china_recognizers(self):
        """注册中国特定的 PII 识别器"""
        # 移除默认的邮箱和 IP 识别器，以及英语 NER 识别器（会在中文文本上产生误报）
        default_recognizers_to_remove = [
            "EmailRecognizer",
            "IpRecognizer",
            "SpacyRecognizer",  # 英语 NER 识别器，在中文上误报严重
        ]
        for rec_name in default_recognizers_to_remove:
            try:
                self.analyzer.registry.remove_recognizer(rec_name)
            except Exception:
                pass

        # 注册自定义识别器
        recognizers = [
            ChinaMobilePhoneRecognizer(),
            ChinaIDCardRecognizer(),
            ChinaBankCardRecognizer(),
            ChinaPassportRecognizer(),
            ChinaSocialCreditCodeRecognizer(),
            ChinaLicensePlateRecognizer(),
            EmailRecognizerCN(),
            IpRecognizerCN(),
            HongKongPhoneRecognizer(),
            HongKongIDCardRecognizer(),
            HongKongNameRecognizer(),
        ]

        for recognizer in recognizers:
            self.analyzer.registry.add_recognizer(recognizer)

    def detect(self, text: str, language: str = "en") -> List[PIIEntity]:
        """
        检测文本中的 PII 实体

        Args:
            text: 待检测文本
            language: 语言代码

        Returns:
            检测到的 PII 实体列表
        """
        results = self.analyzer.analyze(text=text, language=language)

        entities = []
        for r in results:
            if r.score >= self.min_score:
                entities.append(PIIEntity(
                    entity_type=r.entity_type,
                    text=text[r.start:r.end],
                    start=r.start,
                    end=r.end,
                    score=r.score
                ))

        # 中文姓名识别
        if self.enable_name_recognition and self.name_recognizer:
            name_matches = self.name_recognizer.recognize(text)
            for name in name_matches:
                if name.score >= self.min_score:
                    entities.append(PIIEntity(
                        entity_type="PERSON",
                        text=name.text,
                        start=name.start,
                        end=name.end,
                        score=name.score
                    ))

        # 按位置排序并去重
        entities = self._deduplicate_entities(entities)

        return entities

    def _deduplicate_entities(self, entities: List[PIIEntity]) -> List[PIIEntity]:
        """去除重叠和重复的实体"""
        if not entities:
            return entities

        # 按起始位置排序，置信度高的优先
        sorted_entities = sorted(entities, key=lambda x: (x.start, -x.score))

        # 去除重叠实体，保留置信度高的
        result = []
        for entity in sorted_entities:
            # 检查是否与已有实体重叠
            overlap = False
            for existing in result:
                if (entity.start < existing.end and entity.end > existing.start):
                    overlap = True
                    break
            if not overlap:
                result.append(entity)

        return result

    def redact(
        self,
        text: str,
        language: str = "en",
        placeholder_style: str = "type"
    ) -> str:
        """
        对文本中的 PII 进行脱敏处理

        Args:
            text: 待脱敏文本
            language: 语言代码
            placeholder_style: 占位符样式
                - "type": 使用类型标签，如 <手机号>
                - "mask": 使用星号遮盖，如 138****5678

        Returns:
            脱敏后的文本
        """
        entities = self.detect(text, language)

        if not entities:
            return text

        if placeholder_style == "type":
            return self._redact_with_type(text, entities)
        elif placeholder_style == "mask":
            return self._redact_with_mask(text, entities)
        else:
            return self._redact_with_type(text, entities)

    def _redact_with_type(self, text: str, entities: List[PIIEntity]) -> str:
        """使用类型标签进行脱敏"""
        # 从后往前替换，避免索引变化
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)

        result = text
        for entity in sorted_entities:
            placeholder = self.placeholders.get(
                entity.entity_type,
                f"<{entity.entity_type}>"
            )
            result = result[:entity.start] + placeholder + result[entity.end:]

        return result

    def _redact_with_mask(self, text: str, entities: List[PIIEntity]) -> str:
        """使用星号遮盖进行脱敏"""
        sorted_entities = sorted(entities, key=lambda x: x.start, reverse=True)

        result = text
        for entity in sorted_entities:
            original = entity.text
            if len(original) <= 2:
                masked = "*" * len(original)
            else:
                # 保留首尾字符，中间用星号替代
                masked = original[0] + "*" * (len(original) - 2) + original[-1]
            result = result[:entity.start] + masked + result[entity.end:]

        return result

    def check(self, text: str, language: str = "en") -> Tuple[str, List[PIIEntity], bool]:
        """
        完整检查：检测并脱敏

        Args:
            text: 待检查文本
            language: 语言代码

        Returns:
            Tuple[脱敏后文本, 检测到的实体列表, 是否包含PII]
        """
        entities = self.detect(text, language)
        has_pii = len(entities) > 0

        if has_pii:
            redacted = self.redact(text, language)
        else:
            redacted = text

        return redacted, entities, has_pii

    def validate(self, text: str, language: str = "en") -> bool:
        """
        验证文本是否包含 PII

        Args:
            text: 待验证文本
            language: 语言代码

        Returns:
            True 如果文本安全（无 PII），False 如果包含 PII
        """
        entities = self.detect(text, language)
        return len(entities) == 0


def create_guardrail(
    placeholders: Optional[Dict[str, str]] = None,
    min_score: float = 0.5,
    script_type: str = "simplified",
) -> ChinesePIIGuardrail:
    """
    创建中文 PII Guardrail 实例

    Args:
        placeholders: 自定义占位符映射
        min_score: 最小置信度阈值
        script_type: 字体类型，"simplified"（简体）或 "traditional"（繁体）

    Returns:
        ChinesePIIGuardrail 实例
    """
    return ChinesePIIGuardrail(
        placeholders=placeholders,
        min_score=min_score,
        script_type=script_type,
    )


# 便捷函数
def check_pii(text: str) -> Tuple[str, List[PIIEntity], bool]:
    """
    快速检查文本中的 PII

    使用方法:
        safe_text, entities, has_pii = check_pii("我的手机是13812345678")
    """
    guardrail = create_guardrail()
    return guardrail.check(text)


def redact_pii(text: str) -> str:
    """
    快速脱敏文本中的 PII（简体中文）

    使用方法:
        safe_text = redact_pii("身份证：110101199001011234")
        # 输出: "身份证：<身份证号>"
    """
    guardrail = create_guardrail()
    return guardrail.redact(text)


def redact_pii_traditional(text: str) -> str:
    """
    快速脱敏文本中的 PII（繁体中文）

    使用方法:
        safe_text = redact_pii_traditional("身分證字號：110101199001011234")
        # 输出: "身分證字號：<身分證字號>"
    """
    guardrail = create_guardrail(script_type="traditional")
    return guardrail.redact(text)


class UniversalPIIGuardrail:
    """
    通用 PII 安全护栏 - 自动检测中英文并处理

    支持：
    - 简体中文
    - 繁体中文
    - 英文
    - 中英文混合文本

    使用方法:
        guardrail = UniversalPIIGuardrail()

        # 自动检测语言并脱敏
        safe_text = guardrail.redact("我的手机号是13812345678")
        safe_text = guardrail.redact("My phone is 13812345678")
        safe_text = guardrail.redact("手機號是13812345678")
    """

    # 英文占位符
    ENGLISH_PLACEHOLDERS = {
        "CN_PHONE_NUMBER": "<PHONE>",
        "CN_ID_CARD": "<ID_NUMBER>",
        "CN_BANK_CARD": "<BANK_CARD>",
        "CN_PASSPORT": "<PASSPORT>",
        "CN_SOCIAL_CREDIT_CODE": "<BUSINESS_ID>",
        "CN_LICENSE_PLATE": "<LICENSE_PLATE>",
        "EMAIL_ADDRESS": "<EMAIL>",
        "PERSON": "<NAME>",
        "LOCATION": "<LOCATION>",
        "IP_ADDRESS": "<IP_ADDRESS>",
        "URL": "<URL>",
        "PHONE_NUMBER": "<PHONE>",
        "CREDIT_CARD": "<CREDIT_CARD>",
        "HK_PHONE_NUMBER": "<HK_PHONE_NUMBER>",
        "HK_ID_CARD": "<HK_ID_CARD>",
        "HK_NAME": "<HK_NAME>",
    }

    def __init__(
        self,
        placeholders: Optional[Dict[str, str]] = None,
        min_score: float = 0.5,
        default_lang: str = "auto",
    ):
        """
        初始化通用 PII Guardrail

        Args:
            placeholders: 自定义占位符映射
            min_score: 最小置信度阈值
            default_lang: 默认语言，"auto"（自动检测）、"zh"（简体）、"zh-tw"（繁体）、"en"（英文）
        """
        self.min_score = min_score
        self.default_lang = default_lang
        self.custom_placeholders = placeholders or {}

        # 创建三个 guardrail 实例
        self._guardrail_sc = ChinesePIIGuardrail(
            min_score=min_score,
            script_type="simplified"
        )
        self._guardrail_tc = ChinesePIIGuardrail(
            min_score=min_score,
            script_type="traditional"
        )
        self._guardrail_en = ChinesePIIGuardrail(
            min_score=min_score,
            script_type="simplified"
        )
        # 设置英文占位符
        self._guardrail_en.placeholders = {
            **self.ENGLISH_PLACEHOLDERS,
            **self.custom_placeholders
        }

    def _detect_script(self, text: str) -> str:
        """
        检测文本脚本类型

        Returns:
            "simplified", "traditional", 或 "english"
        """
        # 繁体中文特有字符（简体中没有或写法不同的）
        traditional_chars = set(
            '們個時說國過這裡學經動點話書電車頭長問體機開樣東聽聲請義見間實氣報給起錢東邊變還'
            '職傳優確調師產號場歷備據車頭項師畫質議識辦國際視際體際際際際際際際際際際際際際際'
            '機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機機'
            '電話號碼證字聯絡信箱伺服器位址護照統社會信用代碼車輛號牌聯繫方式銀行帳號電子郵件'
            '手機號碼身分證字號護照號碼統一社會信用代碼車牌號碼聯絡信箱電子信箱'
        )

        # 简体中文特有字符
        simplified_chars = set(
            '们个时说国过这里学经动点话书电车头长问体机开样东听声请义见间实气报给起钱东边变还'
            '职传优确调师产号场历备据车头项师画质议识办国际视际体电话号码证字联络信箱服务器地址'
            '护照统社会信用代码车辆号牌联系方式银行账号电子邮件手机号码身份证号码护照号码统一社会'
            '信用代码车牌号码联络信箱电子信箱'
        )

        tc_count = 0
        sc_count = 0
        en_count = 0
        cn_count = 0

        for char in text:
            if '\u4e00' <= char <= '\u9fff':
                cn_count += 1
                if char in traditional_chars:
                    tc_count += 1
                elif char in simplified_chars:
                    sc_count += 1
            elif 'a' <= char.lower() <= 'z':
                en_count += 1

        # 如果没有中文字符，认为是英文
        if cn_count == 0:
            return "english"

        # 根据繁简字符数量判断
        if tc_count > sc_count:
            return "traditional"
        elif sc_count > tc_count:
            return "simplified"
        else:
            # 没有明显差异时，检查特定繁体词组
            traditional_keywords = [
                '手機', '電話', '聯絡', '信箱', '身分證', '身份證', '護照', '銀行卡', '車牌',
                '統一', '代碼', '位址', '伺服器', '客戶', '顧客', '聯絡人', '證件',
            ]
            for kw in traditional_keywords:
                if kw in text:
                    return "traditional"
            return "simplified"

    def _get_guardrail(self, script_type: str) -> ChinesePIIGuardrail:
        """根据脚本类型获取对应的 guardrail"""
        if script_type == "traditional":
            return self._guardrail_tc
        elif script_type == "english":
            return self._guardrail_en
        else:
            return self._guardrail_sc

    def detect(self, text: str) -> List[PIIEntity]:
        """
        检测文本中的 PII 实体

        自动检测语言并使用相应的检测器
        """
        script_type = self._detect_script(text)
        guardrail = self._get_guardrail(script_type)
        return guardrail.detect(text)

    def redact(self, text: str) -> str:
        """
        对文本中的 PII 进行脱敏处理

        自动检测语言并使用相应的占位符
        """
        script_type = self._detect_script(text)
        guardrail = self._get_guardrail(script_type)
        return guardrail.redact(text)

    def check(self, text: str) -> Tuple[str, List[PIIEntity], bool]:
        """
        完整检查：检测并脱敏

        Returns:
            Tuple[脱敏后文本, 检测到的实体列表, 是否包含PII]
        """
        entities = self.detect(text)
        has_pii = len(entities) > 0

        if has_pii:
            redacted = self.redact(text)
        else:
            redacted = text

        return redacted, entities, has_pii

    def validate(self, text: str) -> bool:
        """
        验证文本是否包含 PII

        Returns:
            True 如果文本安全（无 PII），False 如果包含 PII
        """
        entities = self.detect(text)
        return len(entities) == 0


def create_universal_guardrail(
    placeholders: Optional[Dict[str, str]] = None,
    min_score: float = 0.5,
    default_lang: str = "auto",
) -> UniversalPIIGuardrail:
    """
    创建通用 PII Guardrail 实例（自动检测中英文）

    Args:
        placeholders: 自定义占位符映射
        min_score: 最小置信度阈值
        default_lang: 默认语言

    Returns:
        UniversalPIIGuardrail 实例
    """
    return UniversalPIIGuardrail(
        placeholders=placeholders,
        min_score=min_score,
        default_lang=default_lang,
    )


# 统一入口函数
def scan_pii(text: str, lang: str = "auto") -> Tuple[str, List[PIIEntity], bool]:
    """
    统一 PII 扫描入口 - 自动处理中英文

    Args:
        text: 待扫描文本
        lang: 语言，"auto"（自动检测）、"zh"（简体）、"zh-tw"（繁体）、"en"（英文）

    Returns:
        Tuple[脱敏后文本, 检测到的实体列表, 是否包含PII]

    使用方法:
        # 自动检测语言
        safe_text, entities, has_pii = scan_pii("我的手机号是13812345678")
        safe_text, entities, has_pii = scan_pii("My phone is 13812345678")
        safe_text, entities, has_pii = scan_pii("手機號是13812345678")

        # 指定语言
        safe_text, entities, has_pii = scan_pii("Phone: 13812345678", lang="en")
    """
    guardrail = UniversalPIIGuardrail()

    if lang != "auto":
        if lang == "zh":
            guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
            return guardrail_sc.check(text)
        elif lang == "zh-tw":
            guardrail_tc = ChinesePIIGuardrail(script_type="traditional")
            return guardrail_tc.check(text)
        elif lang == "en":
            guardrail_en = ChinesePIIGuardrail(script_type="simplified")
            guardrail_en.placeholders = UniversalPIIGuardrail.ENGLISH_PLACEHOLDERS
            return guardrail_en.check(text)

    return guardrail.check(text)


def mask_pii(text: str, lang: str = "auto") -> str:
    """
    统一 PII 脱敏入口 - 自动处理中英文

    Args:
        text: 待脱敏文本
        lang: 语言，"auto"（自动检测）、"zh"（简体）、"zh-tw"（繁体）、"en"（英文）

    Returns:
        脱敏后的文本

    使用方法:
        safe_text = mask_pii("我的手机号是13812345678")
        # 输出: "我的手机号是<手机号>"

        safe_text = mask_pii("My phone is 13812345678")
        # 输出: "My phone is <PHONE>"

        safe_text = mask_pii("手機號是13812345678")
        # 输出: "手機號是<手機號>"
    """
    safe_text, _, _ = scan_pii(text, lang)
    return safe_text


if __name__ == "__main__":
    print("=" * 70)
    print("通用 PII Guardrail 测试（自动检测中英文）")
    print("=" * 70)

    # 创建通用 guardrail 实例
    guardrail = UniversalPIIGuardrail()

    # 混合语言测试用例
    test_cases = [
        # 简体中文
        ("简体中文", "我的名字叫张伟，手机号是13812345678"),
        ("简体中文", "身份证号：110101199001011234，请核实"),
        # 繁体中文
        ("繁體中文", "我的手機號是13812345678"),
        ("繁體中文", "身分證字號：110101199001011234"),
        # 英文
        ("English", "My name is John Doe and my phone is 13812345678"),
        ("English", "Email: john.doe@example.com, IP: 192.168.1.1"),
        # 中英混合
        ("中英混合", "联系人：张三，Email: zhang@test.com，手机：13912345678"),
        ("中英混合", "Please send to 邮箱wang@example.com or call 13987654321"),
    ]

    for lang_type, text in test_cases:
        print(f"\n{'─' * 60}")
        print(f"[{lang_type}] 原文: {text}")

        # 检测
        entities = guardrail.detect(text)
        print(f"检测到 {len(entities)} 个 PII 实体:")
        for e in entities:
            print(f"  • {e.entity_type}: '{e.text}' (置信度: {e.score:.2f})")

        # 脱敏
        safe_text = guardrail.redact(text)
        print(f"脱敏: {safe_text}")

    # 简体中文专项测试
    print("\n" + "=" * 70)
    print("简体中文 PII Guardrail 测试")
    print("=" * 70)

    guardrail_sc = ChinesePIIGuardrail(script_type="simplified")

    sc_test_cases = [
        "银行卡号：6222021234567890123，开户行：工商银行",
        "护照号：E12345678，有效期至2030年",
        "统一社会信用代码：91110108MA01234567",
        "车牌号：京A12345",
        "联系方式：王经理，电话13987654321，邮箱wang@company.cn",
        "我的IP地址是192.168.1.1",
        "多PII测试：手机13811112222，身份证110101200001011234，邮箱zhang@test.com",
    ]

    for text in sc_test_cases:
        print(f"\n{'─' * 60}")
        print(f"原文: {text}")

        entities = guardrail_sc.detect(text)
        print(f"检测到 {len(entities)} 个 PII 实体:")
        for e in entities:
            print(f"  • {e.entity_type}: '{e.text}' (置信度: {e.score:.2f})")

        safe_text = guardrail_sc.redact(text)
        print(f"脱敏: {safe_text}")

    # 繁体中文测试
    print("\n" + "=" * 70)
    print("繁體中文 PII Guardrail 測試")
    print("=" * 70)

    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")

    traditional_test_cases = [
        "我的手機號是13812345678",
        "身分證字號：110101199001011234",
        "銀行卡號：6222021234567890123",
        "護照號碼：E12345678",
        "統一社會信用代碼：91110108MA01234567",
        "車牌號碼：京A12345",
        "聯絡信箱：wang@company.cn",
        "伺服器IP位址：192.168.1.1",
    ]

    for text in traditional_test_cases:
        print(f"\n{'─' * 60}")
        print(f"原文: {text}")

        entities = guardrail_tc.detect(text)
        print(f"檢測到 {len(entities)} 個 PII 實體:")
        for e in entities:
            print(f"  • {e.entity_type}: '{e.text}' (置信度: {e.score:.2f})")

        safe_text = guardrail_tc.redact(text)
        print(f"脫敏: {safe_text}")
