"""
香港 PII 识别器测试

测试香港电话和身份证识别功能
"""

from chinese_guardrail import ChinesePIIGuardrail, UniversalPIIGuardrail


def test_hk_phone_number():
    """测试香港电话识别"""
    print("=" * 70)
    print("香港电话识别测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        # 基本格式
        ("51234567", "基本8位数字"),
        ("91234567", "9开头手机号"),
        ("68765432", "6开头手机号"),
        ("78765432", "7开头手机号"),
        ("88765432", "8开头手机号"),

        # 带空格格式
        ("5678 1234", "带空格格式"),
        ("9123 4567", "9开头带空格"),

        # 带上下文
        ("手機：91234567", "繁体上下文"),
        ("聯絡電話：51234567", "繁体联络电话"),
        ("Tel: 68765432", "英文上下文"),
        ("Mobile: 91234567", "英文Mobile"),
        ("Contact: 5678 1234", "英文Contact带空格"),
    ]

    passed = 0
    failed = 0

    for text, desc in test_cases:
        entities = guardrail.detect(text)
        hk_phones = [e for e in entities if e.entity_type == "HK_PHONE_NUMBER"]

        if hk_phones:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 检测到: {hk_phones[0].text}")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 未检测到香港电话")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_hk_id_card():
    """测试香港身份证识别"""
    print("\n" + "=" * 70)
    print("香港身份证识别测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        # 单字母格式
        ("A123456(7)", "单字母+数字校验"),
        ("A123456(A)", "单字母+字母校验"),
        ("B654321(0)", "B开头"),
        ("C789012(9)", "C开头"),

        # 双字母格式
        ("AB123456(7)", "双字母+数字校验"),
        ("AB123456(A)", "双字母+字母校验"),
        ("CD654321(3)", "CD开头"),
        ("YZ789012(A)", "YZ开头"),

        # 带上下文
        ("身份證：A123456(7)", "繁体上下文"),
        ("HKID: AB123456(A)", "英文HKID"),
        ("ID card: C654321(3)", "英文ID card"),
        ("證件號碼：YZ789012(A)", "繁体证件号码"),
    ]

    passed = 0
    failed = 0

    for text, desc in test_cases:
        entities = guardrail.detect(text)
        hk_ids = [e for e in entities if e.entity_type == "HK_ID_CARD"]

        if hk_ids:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 检测到: {hk_ids[0].text}")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 未检测到香港身份证")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_redaction():
    """测试脱敏功能"""
    print("\n" + "=" * 70)
    print("脱敏功能测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        ("手機：91234567", "手機：<香港电话>"),
        ("身份證：A123456(7)", "身份證：<香港身份证>"),
        ("聯絡電話：51234567，HKID: AB123456(A)", "聯絡電話：<香港电话>，HKID: <香港身份证>"),
    ]

    passed = 0
    failed = 0

    for text, expected in test_cases:
        result = guardrail.redact(text)
        if result == expected:
            passed += 1
            print(f"✓ '{text}' -> '{result}'")
        else:
            failed += 1
            print(f"✗ '{text}'")
            print(f"  期望: '{expected}'")
            print(f"  实际: '{result}'")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_distinction_from_mainland():
    """测试香港与大陆PII区分"""
    print("\n" + "=" * 70)
    print("香港 vs 大陆 PII 区分测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        # (文本, 期望类型, 描述)
        ("手机：13812345678", "CN_PHONE_NUMBER", "大陆手机(11位,1开头)"),
        ("手機：91234567", "HK_PHONE_NUMBER", "香港电话(8位,9开头)"),
        ("身份证：110101199001011234", "CN_ID_CARD", "大陆身份证(18位)"),
        ("身份證：A123456(7)", "HK_ID_CARD", "香港身份证(字母+括号)"),
    ]

    passed = 0
    failed = 0

    for text, expected_type, desc in test_cases:
        entities = guardrail.detect(text)
        if entities and entities[0].entity_type == expected_type:
            passed += 1
            print(f"✓ [{desc}] 检测为 {expected_type}")
        else:
            failed += 1
            actual = entities[0].entity_type if entities else "无"
            print(f"✗ [{desc}] 期望 {expected_type}, 实际 {actual}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_mixed_content():
    """测试混合内容"""
    print("\n" + "=" * 70)
    print("混合内容测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    text = """
    客户信息登记表

    大陆客户：
    姓名：张三
    手机：13812345678
    身份证：110101199001011234

    香港客户：
    姓名：Wong Yan Yee
    手機：91234567
    身份證：AB123456(A)

    Hong Kong Customer:
    Name: Chan Tai Man
    Phone: 91234568
    ID No: P115757(7)

    联系方式：
    邮箱：test@example.com
    IP：192.168.1.1
    """

    print("原文:")
    print(text)

    entities = guardrail.detect(text)
    print(f"\n检测到 {len(entities)} 个 PII 实体:")
    for e in entities:
        print(f"  • {e.entity_type}: '{e.text}'")

    safe_text = guardrail.redact(text)
    print("\n脱敏后:")
    print(safe_text)

    return True


def test_traditional_chinese():
    """测试繁体中文模式"""
    print("\n" + "=" * 70)
    print("繁体中文模式测试")
    print("=" * 70)

    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")

    test_cases = [
        "手機號碼：91234567",
        "香港身份證：A123456(7)",
        "聯絡方式：電話5678 1234，HKID: AB123456(A)",
    ]

    for text in test_cases:
        entities = guardrail_tc.detect(text)
        safe = guardrail_tc.redact(text)
        print(f"\n原文: {text}")
        print(f"脱敏: {safe}")

    return True


def test_universal_guardrail():
    """测试通用Guardrail"""
    print("\n" + "=" * 70)
    print("UniversalPIIGuardrail 测试（自动语言检测）")
    print("=" * 70)

    guardrail = UniversalPIIGuardrail()

    test_cases = [
        # 简体中文
        ("大陆手机13812345678", "simplified"),
        # 繁体中文
        ("香港手機91234567", "traditional"),
        ("身份證AB123456(A)", "traditional"),
        # 英文
        ("Phone: 91234567, HKID: A123456(7)", "english"),
    ]

    for text, expected_script in test_cases:
        script = guardrail._detect_script(text)
        entities = guardrail.detect(text)
        safe = guardrail.redact(text)

        print(f"\n原文: {text}")
        print(f"检测语言: {script} (期望: {expected_script})")
        print(f"检测到: {[e.entity_type for e in entities]}")
        print(f"脱敏: {safe}")

    return True


def test_edge_cases():
    """测试边界情况"""
    print("\n" + "=" * 70)
    print("边界情况测试")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    # 不应被识别为香港电话的情况
    not_hk_phone = [
        ("12345678", "1开头不应识别"),  # 香港电话5-9开头
        ("2345678", "7位数字"),
        ("41234567", "4开头不应识别"),
        ("01234567", "0开头不应识别"),
    ]

    # 不应被识别为香港身份证的情况
    not_hk_id = [
        ("A1234567", "无括号"),
        ("A123456(10)", "括号内两位数"),
        ("123456(7)", "无字母前缀"),
        ("ABC123456(7)", "三字母前缀"),
    ]

    print("\n不应识别为香港电话:")
    for text, desc in not_hk_phone:
        entities = guardrail.detect(text)
        hk_phones = [e for e in entities if e.entity_type == "HK_PHONE_NUMBER"]
        if not hk_phones:
            print(f"✓ [{desc}] '{text}' 正确不识别")
        else:
            print(f"✗ [{desc}] '{text}' 错误识别为香港电话")

    print("\n不应识别为香港身份证:")
    for text, desc in not_hk_id:
        entities = guardrail.detect(text)
        hk_ids = [e for e in entities if e.entity_type == "HK_ID_CARD"]
        if not hk_ids:
            print(f"✓ [{desc}] '{text}' 正确不识别")
        else:
            print(f"✗ [{desc}] '{text}' 错误识别为香港身份证")

    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("香港 PII 识别器完整测试套件")
    print("=" * 70)

    results = {
        "香港电话识别": test_hk_phone_number(),
        "香港身份证识别": test_hk_id_card(),
        "脱敏功能": test_redaction(),
        "大陆区分": test_distinction_from_mainland(),
        "混合内容": test_mixed_content(),
        "繁体中文模式": test_traditional_chinese(),
        "通用Guardrail": test_universal_guardrail(),
        "边界情况": test_edge_cases(),
    }

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {name}")

    total_passed = sum(1 for v in results.values() if v)
    print(f"\n总计: {total_passed}/{len(results)} 通过")

    return all(results.values())


if __name__ == "__main__":
    run_all_tests()
