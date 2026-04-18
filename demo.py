"""
中文 PII Guardrail 完整示例

展示如何在实际场景中使用中文 PII 检测和脱敏功能。
"""

from chinese_guardrail import (
    ChinesePIIGuardrail,
    UniversalPIIGuardrail,
    create_guardrail,
    create_universal_guardrail,
    check_pii,
    redact_pii,
    scan_pii,
    mask_pii,
)


def demo_unified_entry():
    """统一入口演示（自动检测中英文）"""
    print("=" * 70)
    print("统一入口演示（自动检测中英文）")
    print("=" * 70)

    test_cases = [
        # 简体中文
        "我的手机号是13812345678",
        "身份证号：110101199001011234",
        # 繁体中文
        "我的手機號是13812345678",
        "身分證字號：110101199001011234",
        # 英文
        "My phone is 13812345678",
        "Email: john@example.com, IP: 192.168.1.1",
        # 中英混合
        "联系人：张三，Email: zhang@test.com",
    ]

    print("\n使用 mask_pii() 快速脱敏:")
    for text in test_cases:
        safe_text = mask_pii(text)
        print(f"  原文: {text}")
        print(f"  脱敏: {safe_text}\n")

    # 详细信息
    print("使用 scan_pii() 获取详细信息:")
    text = "手机：13812345678，邮箱：test@example.com"
    safe_text, entities, has_pii = scan_pii(text)
    print(f"  原文: {text}")
    print(f"  脱敏: {safe_text}")
    print(f"  检测到的 PII: {[f'{e.entity_type}={e.text}' for e in entities]}")
    print(f"  是否包含 PII: {has_pii}")


def demo_basic_usage():
    """基础用法演示"""
    print("=" * 70)
    print("基础用法")
    print("=" * 70)

    # 方式1：快速函数
    text = "我的手机号是13812345678，身份证号是110101199001011234"
    safe_text = redact_pii(text)
    print(f"原文: {text}")
    print(f"脱敏: {safe_text}")

    # 方式2：获取详细信息
    safe_text, entities, has_pii = check_pii(text)
    print(f"\n检测详情:")
    for e in entities:
        print(f"  - {e.entity_type}: {e.text}")
    print(f"是否包含PII: {has_pii}")


def demo_custom_guardrail():
    """自定义 Guardrail 配置"""
    print("\n" + "=" * 70)
    print("自定义配置")
    print("=" * 70)

    # 自定义占位符
    custom_placeholders = {
        "CN_PHONE_NUMBER": "[电话已隐藏]",
        "CN_ID_CARD": "[身份证已隐藏]",
        "EMAIL_ADDRESS": "[邮箱已隐藏]",
    }

    guardrail = create_guardrail(
        placeholders=custom_placeholders,
        min_score=0.7  # 设置置信度阈值
    )

    text = "联系人：张三，手机：13912345678，邮箱：zhang@test.com"
    safe_text = guardrail.redact(text)
    print(f"原文: {text}")
    print(f"脱敏: {safe_text}")


def demo_mask_style():
    """星号遮盖样式"""
    print("\n" + "=" * 70)
    print("星号遮盖样式")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()
    text = "银行卡号：6222021234567890123"

    # 类型标签
    safe_type = guardrail.redact(text, placeholder_style="type")
    print(f"类型标签: {safe_type}")

    # 星号遮盖
    safe_mask = guardrail.redact(text, placeholder_style="mask")
    print(f"星号遮盖: {safe_mask}")


def demo_llm_output_filter():
    """LLM 输出过滤示例"""
    print("\n" + "=" * 70)
    print("LLM 输出过滤示例")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    # 模拟 LLM 输出
    llm_outputs = [
        "根据您提供的信息，张先生的手机号是13812345678，我们已记录。",
        "用户身份证号110101199001011234已验证通过。",
        "订单已发送至邮箱customer@example.com，请查收。",
        "服务器IP地址192.168.1.100已配置完成。",
    ]

    print("原始 LLM 输出 -> 过滤后输出:")
    for output in llm_outputs:
        filtered = guardrail.redact(output)
        print(f"\n原始: {output}")
        print(f"过滤: {filtered}")


def demo_all_pii_types():
    """所有支持的 PII 类型"""
    print("\n" + "=" * 70)
    print("支持的 PII 类型")
    print("=" * 70)

    test_cases = {
        "手机号": "我的手机号是13812345678",
        "身份证号": "身份证号：110101199001011234",
        "银行卡号": "银行卡号：6222021234567890123",
        "护照号": "护照号：E12345678",
        "统一社会信用代码": "统一社会信用代码：91110108MA01234567",
        "车牌号": "车牌号：京A12345",
        "邮箱": "联系邮箱：zhangsan@example.com",
        "IP地址": "服务器IP：192.168.1.100",
    }

    guardrail = ChinesePIIGuardrail()

    for pii_type, text in test_cases.items():
        entities = guardrail.detect(text)
        safe_text = guardrail.redact(text)
        print(f"\n{pii_type}:")
        print(f"  原文: {text}")
        print(f"  脱敏: {safe_text}")
        if entities:
            print(f"  置信度: {entities[0].score:.2f}")


def demo_validation():
    """验证文本安全性"""
    print("\n" + "=" * 70)
    print("文本安全性验证")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    texts = [
        "这是一段普通的文本，没有任何敏感信息。",
        "联系电话：13812345678",
    ]

    for text in texts:
        is_safe = guardrail.validate(text)
        status = "✅ 安全" if is_safe else "⚠️ 包含敏感信息"
        print(f"{status}: {text}")


def demo_traditional_chinese():
    """繁体中文支持演示"""
    print("\n" + "=" * 70)
    print("繁體中文支援")
    print("=" * 70)

    # 创建繁体中文 guardrail
    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")

    test_cases = [
        "我的手機號是13812345678",
        "身分證字號：110101199001011234",
        "銀行卡號：6222021234567890123",
        "護照號碼：E12345678",
        "聯絡信箱：wang@company.cn",
        "伺服器IP位址：192.168.1.1",
    ]

    print("繁體中文測試結果:")
    for text in test_cases:
        entities = guardrail_tc.detect(text)
        safe_text = guardrail_tc.redact(text)
        print(f"\n原文: {text}")
        print(f"脫敏: {safe_text}")


if __name__ == "__main__":
    demo_unified_entry()
    demo_basic_usage()
    demo_custom_guardrail()
    demo_mask_style()
    demo_llm_output_filter()
    demo_all_pii_types()
    demo_validation()
    demo_traditional_chinese()

    print("\n" + "=" * 70)
    print("演示完成")
    print("=" * 70)
