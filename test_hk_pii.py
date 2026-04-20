"""
香港 PII 识别器测试

测试香港电话、身份证和姓名识别功能
"""

from chinese_guardrail import ChinesePIIGuardrail, UniversalPIIGuardrail


def test_hk_name():
    """测试香港英文姓名识别 - 简体、繁体、英文三语场景"""
    print("=" * 70)
    print("香港英文姓名识别测试 (简体/繁体/英文)")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    # 应该被识别的情况（有上下文）
    positive_cases = [
        # ========== 简体中文场景 ==========
        ("姓名：Wong Yan Yee", "简体", "姓名上下文"),
        ("客户：Chan Tai Man", "简体", "客户上下文"),
        ("联系人：Lee Chi Wai", "简体", "联系人上下文"),
        ("客户姓名：Cheung Ka Keung", "简体", "客户姓名上下文"),
        ("名字：Lam Hoi Yan", "简体", "名字上下文"),

        # ========== 繁体中文场景 ==========
        ("客戶姓名：Chan Tai Man", "繁体", "客戶姓名上下文"),
        ("聯絡人：Lee Ming", "繁体", "聯絡人上下文"),
        ("姓名：Wong Siu Ming", "繁体", "姓名上下文"),
        ("顧客：Ho Ka Yan", "繁体", "顧客上下文"),
        ("持有人：Yip Tsz Chun", "繁体", "持有人上下文"),

        # ========== 英文场景 - 标准关键词 ==========
        ("Name: Chan Tai Man", "英文", "Name上下文"),
        ("Customer: Wong Yan Yee", "英文", "Customer上下文"),
        ("Contact: Lee Chi Wai", "英文", "Contact上下文"),
        ("Client: Lam Hoi Yan", "英文", "Client上下文"),
        ("User: Cheung Ka Keung", "英文", "User上下文"),

        # ========== 英文场景 - 变体关键词 ==========
        ("Contact Person: Ho Ka Yan", "英文", "Contact Person"),
        ("Full Name: Yip Tsz Chun", "英文", "Full Name"),
        ("Account Holder: Wong Siu Ming", "英文", "Account Holder"),
        ("Customer Name: Chan Ka Ming", "英文", "Customer Name"),
        ("Client Name: Lee Chi Fai", "英文", "Client Name"),
        ("Applicant: Cheung Wai Man", "英文", "Applicant"),
        ("Representative: Lam Ka Ho", "英文", "Representative"),
    ]

    # 不应被识别的情况（无上下文）
    negative_cases = [
        # 英文无上下文
        ("Wong Yan Yee went to the store", "英文无上下文句子"),
        ("Chan Tai Man is a student", "英文无上下文描述"),
        ("The winner is Lee Chi Wai", "英文无关键词"),
        ("My friend John Smith", "非香港英文姓名"),
        ("Visit Hong Kong with Peter Lee", "英文叙述无上下文"),

        # 中文无上下文（简体/繁体）
        ("Wong Yan Yee 去商店", "中文混合无上下文"),
        ("Chan Tai Man 是一個學生", "繁体混合无上下文"),

        # 大小写变体（应该识别但测试不同大小写）
        ("name: wong yan yee", "全小写姓名"),
        ("NAME: CHAN TAI MAN", "全大写姓名"),
    ]

    passed = 0
    failed = 0

    print("\n应识别为 HK_NAME:")
    for text, lang, desc in positive_cases:
        entities = guardrail.detect(text)
        hk_names = [e for e in entities if e.entity_type == "HK_NAME"]

        if hk_names:
            passed += 1
            print(f"✓ [{lang}][{desc}] '{text}' -> 检测到: {hk_names[0].text}")
        else:
            failed += 1
            print(f"✗ [{lang}][{desc}] '{text}' -> 未检测到香港姓名")

    print("\n不应识别为 HK_NAME（无上下文）:")
    for text, desc in negative_cases:
        entities = guardrail.detect(text)
        hk_names = [e for e in entities if e.entity_type == "HK_NAME"]

        if not hk_names:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 错误识别为: {hk_names[0].text}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_hk_phone_number():
    """测试香港电话识别 - 简体、繁体、英文三语场景"""
    print("=" * 70)
    print("香港电话识别测试 (简体/繁体/英文)")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        # ========== 基本格式（无上下文）==========
        ("51234567", "基本8位数字（5开头）"),
        ("61234567", "基本8位数字（6开头）"),
        ("78765432", "7开头手机号"),
        ("88765432", "8开头手机号"),
        ("91234567", "9开头手机号"),

        # ========== 带空格格式 ==========
        ("5123 4567", "5开头带空格"),
        ("5678 1234", "带空格格式"),
        ("9123 4567", "9开头带空格"),
        ("9123-4567", "连字符格式"),
        ("9876 5432", "9开头空格分隔"),

        # ========== 带+852国际区号格式 ==========
        ("+85291234567", "国际格式无空格"),
        ("+852 91234567", "国际格式有空格"),
        ("+852 9123 4567", "国际格式带空格"),
        ("852-91234567", "区号连字符"),
        ("85291234567", "区号无分隔符"),

        # ========== 简体中文场景 ==========
        ("手机：61234567", "简体手机上下文"),
        ("电话：51234567", "简体电话上下文"),
        ("联系电话：91234567", "简体联系电话"),
        ("手机号：68765432", "简体手机号上下文"),
        ("号码：51234567", "简体号码上下文"),
        ("致电：91234567", "简体致电上下文"),

        # ========== 繁体中文场景 ==========
        ("手機：91234567", "繁体手機上下文"),
        ("電話：51234567", "繁体電話上下文"),
        ("聯絡電話：61234567", "繁体聯絡電話"),
        ("手機號碼：98765432", "繁体手機號碼"),
        ("號碼：51234567", "繁体號碼上下文"),
        ("致電：91234567", "繁体致電上下文"),
        ("熱線：51234567", "繁体熱線上下文"),

        # ========== 英文场景 - 标准关键词 ==========
        ("Tel: 68765432", "英文Tel上下文"),
        ("Tel.: 51234567", "英文Tel.带句号"),
        ("Mobile: 91234567", "英文Mobile上下文"),
        ("Phone: 78765432", "英文Phone上下文"),
        ("Contact: 5678 1234", "英文Contact带空格"),

        # ========== 英文场景 - 变体关键词 ==========
        ("Telephone: 61234567", "英文Telephone完整词"),
        ("Cell: 91234567", "英文Cell缩写"),
        ("Cellphone: 88765432", "英文Cellphone完整词"),
        ("Cellular: 51234567", "英文Cellular"),
        ("Number: 91234567", "英文Number上下文"),
        ("Call: 61234567", "英文Call上下文"),
        ("Hotline: 51234567", "英文Hotline上下文"),

        # ========== 混合中英文场景 ==========
        ("Tel: 手機91234567", "混合Tel+繁体手機"),
        ("Contact: 电话51234567", "混合Contact+简体电话"),
    ]

    # 不应识别的情况
    negative_cases = [
        ("12345678", "1开头不应识别"),
        ("2345678", "7位数字"),
        ("41234567", "4开头不应识别"),
        ("01234567", "0开头不应识别"),
        ("512345678", "9位数字"),
        ("5123456", "7位数字"),
        ("13812345678", "大陆11位手机号"),
        ("+8613812345678", "大陆手机国际格式"),
    ]

    passed = 0
    failed = 0

    print("\n应识别为 HK_PHONE_NUMBER:")
    for text, desc in test_cases:
        entities = guardrail.detect(text)
        hk_phones = [e for e in entities if e.entity_type == "HK_PHONE_NUMBER"]

        if hk_phones:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 检测到: {hk_phones[0].text}")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 未检测到香港电话")

    print("\n不应识别为 HK_PHONE_NUMBER:")
    for text, desc in negative_cases:
        entities = guardrail.detect(text)
        hk_phones = [e for e in entities if e.entity_type == "HK_PHONE_NUMBER"]

        if not hk_phones:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 错误识别为: {hk_phones[0].text}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_hk_id_card():
    """测试香港身份证识别 - 简体、繁体、英文三语场景"""
    print("\n" + "=" * 70)
    print("香港身份证识别测试 (简体/繁体/英文)")
    print("=" * 70)

    guardrail = ChinesePIIGuardrail()

    test_cases = [
        # ========== 单字母格式 ==========
        ("A123456(7)", "基本", "单字母A+数字校验"),
        ("A123456(A)", "基本", "单字母A+字母校验"),
        ("B654321(0)", "基本", "B开头+数字校验"),
        ("B654321(B)", "基本", "B开头+字母校验"),
        ("C789012(9)", "基本", "C开头"),
        ("D123456(0)", "基本", "D开头"),
        ("E987654(1)", "基本", "E开头"),
        ("F111111(2)", "基本", "F开头"),
        ("G222222(3)", "基本", "G开头"),
        ("H333333(4)", "基本", "H开头"),
        ("K444444(5)", "基本", "K开头"),
        ("L555555(6)", "基本", "L开头"),
        ("M666666(7)", "基本", "M开头"),
        ("N777777(8)", "基本", "N开头"),
        ("P888888(9)", "基本", "P开头"),
        ("R999999(A)", "基本", "R开头"),
        ("S000000(B)", "基本", "S开头"),
        ("T123456(7)", "基本", "T开头"),
        ("V654321(8)", "基本", "V开头"),
        ("W789012(9)", "基本", "W开头"),
        ("X123456(0)", "基本", "X开头"),
        ("Y654321(1)", "基本", "Y开头"),
        ("Z789012(2)", "基本", "Z开头"),

        # ========== 双字母格式 ==========
        ("AB123456(7)", "基本", "双字母AB+数字校验"),
        ("AB123456(A)", "基本", "双字母AB+字母校验"),
        ("CD654321(3)", "基本", "CD开头"),
        ("EF123456(4)", "基本", "EF开头"),
        ("GH789012(5)", "基本", "GH开头"),
        ("KJ654321(6)", "基本", "KJ开头"),
        ("LM123456(7)", "基本", "LM开头"),
        ("NP789012(8)", "基本", "NP开头"),
        ("RS654321(9)", "基本", "RS开头"),
        ("TW123456(A)", "基本", "TW开头"),
        ("VZ789012(B)", "基本", "VZ开头"),
        ("WX123456(0)", "基本", "WX开头"),
        ("YZ789012(A)", "基本", "YZ开头"),

        # ========== 简体中文场景 ==========
        ("身份证：A123456(7)", "简体", "身份证上下文"),
        ("香港身份证：AB123456(A)", "简体", "香港身份证"),
        ("证件号码：C654321(3)", "简体", "证件号码上下文"),
        ("证件号：D123456(4)", "简体", "证件号简写"),
        ("身份证号：E987654(5)", "简体", "身份证号完整"),
        ("ID：F111111(6)", "简体", "ID上下文"),
        ("HK ID：G222222(7)", "简体", "HK ID上下文"),

        # ========== 繁体中文场景 ==========
        ("身份證：A123456(7)", "繁体", "身份證上下文"),
        ("香港身份證：AB123456(A)", "繁体", "香港身份證"),
        ("證件號碼：C654321(3)", "繁体", "證件號碼上下文"),
        ("證件號：D123456(4)", "繁体", "證件號简写"),
        ("身份證號碼：E987654(5)", "繁体", "身份證號碼完整"),
        ("身分證：F111111(6)", "繁体", "身分證变体"),
        ("香港身分證：G222222(7)", "繁体", "香港身分證"),

        # ========== 英文场景 - 标准关键词 ==========
        ("HKID: A123456(7)", "英文", "HKID缩写"),
        ("HK ID: AB123456(A)", "英文", "HK ID带空格"),
        ("ID: C654321(3)", "英文", "ID上下文"),
        ("ID card: D123456(4)", "英文", "ID card完整"),
        ("HKID Card: E987654(5)", "英文", "HKID Card"),

        # ========== 英文场景 - 变体关键词 ==========
        ("Identity Card: A123456(7)", "英文", "Identity Card完整"),
        ("Hong Kong ID: B654321(0)", "英文", "Hong Kong ID"),
        ("HK Identity: C789012(9)", "英文", "HK Identity"),
        ("Card Number: D123456(1)", "英文", "Card Number"),
        ("ID Number: E654321(2)", "英文", "ID Number"),
        ("Identification: F789012(3)", "英文", "Identification"),
        ("Document: G123456(4)", "英文", "Document上下文"),
        ("Document No: H654321(5)", "英文", "Document No"),

        # ========== 混合场景 ==========
        ("HKID: 身份證A123456(7)", "混合", "HKID+繁体"),
        ("ID Card: 身份证AB123456(A)", "混合", "ID Card+简体"),
    ]

    # 不应识别的情况
    negative_cases = [
        ("A1234567", "无括号"),
        ("A123456(10)", "括号内两位数"),
        ("123456(7)", "无字母前缀"),
        ("ABC123456(7)", "三字母前缀"),
        ("A12345(7)", "5位数字"),
        ("A1234567(7)", "7位数字"),
        ("110101199001011234", "大陆身份证"),
        ("A-123456-7", "连字符分隔"),
    ]

    passed = 0
    failed = 0

    print("\n应识别为 HK_ID_CARD:")
    for text, lang, desc in test_cases:
        entities = guardrail.detect(text)
        hk_ids = [e for e in entities if e.entity_type == "HK_ID_CARD"]

        if hk_ids:
            passed += 1
            print(f"✓ [{lang}][{desc}] '{text}' -> 检测到: {hk_ids[0].text}")
        else:
            failed += 1
            print(f"✗ [{lang}][{desc}] '{text}' -> 未检测到香港身份证")

    print("\n不应识别为 HK_ID_CARD:")
    for text, desc in negative_cases:
        entities = guardrail.detect(text)
        hk_ids = [e for e in entities if e.entity_type == "HK_ID_CARD"]

        if not hk_ids:
            passed += 1
            print(f"✓ [{desc}] '{text}' -> 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' -> 错误识别为: {hk_ids[0].text}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_redaction():
    """测试脱敏功能 - 简体、繁体、英文三语场景"""
    print("\n" + "=" * 70)
    print("脱敏功能测试 (简体/繁体/英文)")
    print("=" * 70)

    # 简体场景
    guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
    # 繁体场景
    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")
    # 英文场景 - 使用英文占位符
    from chinese_guardrail import UniversalPIIGuardrail
    guardrail_en = ChinesePIIGuardrail(
        script_type="simplified",
        placeholders=UniversalPIIGuardrail.ENGLISH_PLACEHOLDERS
    )

    test_cases = [
        # ========== 简体中文场景 ==========
        (guardrail_sc, "手机：91234567", "手机：<香港电话>"),
        (guardrail_sc, "联系电话：51234567", "联系电话：<香港电话>"),
        (guardrail_sc, "香港身份证：A123456(7)", "香港身份证：<香港身份证>"),
        (guardrail_sc, "证件号码：AB123456(A)", "证件号码：<香港身份证>"),
        (guardrail_sc, "客户：Wong Tai Man，手机：91234567",
         "客户：<香港姓名>，手机：<香港电话>"),

        # ========== 繁体中文场景 ==========
        (guardrail_tc, "手機：91234567", "手機：<香港電話>"),
        (guardrail_tc, "聯絡電話：51234567", "聯絡電話：<香港電話>"),
        (guardrail_tc, "香港身份證：A123456(7)", "香港身份證：<香港身份證>"),
        (guardrail_tc, "證件號碼：AB123456(A)", "證件號碼：<香港身份證>"),
        (guardrail_tc, "聯絡人：Wong Tai Man，手機：91234567",
         "聯絡人：<香港姓名>，手機：<香港電話>"),

        # ========== 英文场景 ==========
        (guardrail_en, "Mobile: 91234567", "Mobile: <HK_PHONE_NUMBER>"),
        (guardrail_en, "Phone: 51234567", "Phone: <HK_PHONE_NUMBER>"),
        (guardrail_en, "HKID: A123456(7)", "HKID: <HK_ID_CARD>"),
        (guardrail_en, "ID Card: AB123456(A)", "ID Card: <HK_ID_CARD>"),
        (guardrail_en, "Name: Wong Tai Man, Phone: 91234567",
         "Name: <HK_NAME>, Phone: <HK_PHONE_NUMBER>"),
    ]

    passed = 0
    failed = 0

    for guardrail, text, expected in test_cases:
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
    """测试香港与大陆PII区分 - 简体、繁体、英文三语场景"""
    print("\n" + "=" * 70)
    print("香港 vs 大陆 PII 区分测试 (简体/繁体/英文)")
    print("=" * 70)

    guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")
    guardrail_en = ChinesePIIGuardrail(script_type="simplified")

    test_cases = [
        # ========== 手机/电话区分 ==========
        # 简体中文
        (guardrail_sc, "手机：13812345678", "CN_PHONE_NUMBER", "简体-大陆手机(11位)"),
        (guardrail_sc, "电话：91234567", "HK_PHONE_NUMBER", "简体-香港电话(8位)"),
        (guardrail_sc, "联系电话：51234567", "HK_PHONE_NUMBER", "简体-香港电话(5开头)"),
        (guardrail_sc, "手机号：68765432", "HK_PHONE_NUMBER", "简体-香港电话(6开头)"),

        # 繁体中文
        (guardrail_tc, "手機：91234567", "HK_PHONE_NUMBER", "繁体-香港电话(8位)"),
        (guardrail_tc, "聯絡電話：51234567", "HK_PHONE_NUMBER", "繁体-香港电话(5开头)"),

        # 英文
        (guardrail_en, "Mobile: 13812345678", "CN_PHONE_NUMBER", "英文-大陆手机"),
        (guardrail_en, "Phone: 91234567", "HK_PHONE_NUMBER", "英文-香港电话(8位)"),
        (guardrail_en, "Tel: 61234567", "HK_PHONE_NUMBER", "英文-香港电话(6开头)"),

        # ========== 身份证区分 ==========
        # 简体中文
        (guardrail_sc, "身份证：110101199001011234", "CN_ID_CARD", "简体-大陆身份证(18位)"),
        (guardrail_sc, "香港身份证：A123456(7)", "HK_ID_CARD", "简体-香港身份证(字母+括号)"),
        (guardrail_sc, "证件号码：AB123456(A)", "HK_ID_CARD", "简体-香港身份证(双字母)"),

        # 繁体中文
        (guardrail_tc, "身份證：A123456(7)", "HK_ID_CARD", "繁体-香港身份证(字母+括号)"),
        (guardrail_tc, "證件號碼：AB123456(A)", "HK_ID_CARD", "繁体-香港身份证(双字母)"),

        # 英文
        (guardrail_en, "ID Card: 110101199001011234", "CN_ID_CARD", "英文-大陆身份证"),
        (guardrail_en, "HKID: A123456(7)", "HK_ID_CARD", "英文-香港身份证(单字母)"),
        (guardrail_en, "Hong Kong ID: AB123456(A)", "HK_ID_CARD", "英文-香港身份证(双字母)"),
    ]

    passed = 0
    failed = 0

    for guardrail, text, expected_type, desc in test_cases:
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
    """测试混合内容 - 简体、繁体、英文三语混合场景"""
    print("\n" + "=" * 70)
    print("混合内容测试 (简体/繁体/英文三语混合)")
    print("=" * 70)

    # 简体场景
    guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
    # 繁体场景
    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")

    # ========== 简体中文为主的混合场景 ==========
    text_sc = """
    客户信息登记表

    大陆客户:
    姓名：张三
    手机：13812345678
    身份证：110101199001011234

    香港客户:
    姓名：Wong Yan Yee
    电话：91234567
    香港身份证：AB123456(A)

    联系邮箱: test@example.com
    """

    print("【简体中文场景】原文:")
    print(text_sc)

    entities = guardrail_sc.detect(text_sc)
    print(f"\n检测到 {len(entities)} 个 PII 实体:")
    for e in entities:
        print(f"  • {e.entity_type}: '{e.text}'")

    safe_text = guardrail_sc.redact(text_sc)
    print("\n脱敏后:")
    print(safe_text)

    # ========== 繁体中文为主的混合场景 ==========
    text_tc = """
    客戶資料登記表

    香港客戶:
    客戶姓名：Chan Tai Man
    手機號碼：91234567
    香港身份證：A123456(7)

    聯絡資訊:
    電郵: test@example.com
    """

    print("\n" + "-" * 70)
    print("【繁体中文场景】原文:")
    print(text_tc)

    entities = guardrail_tc.detect(text_tc)
    print(f"\n检测到 {len(entities)} 个 PII 实体:")
    for e in entities:
        print(f"  • {e.entity_type}: '{e.text}'")

    safe_text = guardrail_tc.redact(text_tc)
    print("\n脱敏后:")
    print(safe_text)

    # ========== 三语混合场景（繁体版） ==========
    text_mixed = """
    Customer Registration / 客戶登記 / 客户登记

    English:
    Name: Wong Siu Ming
    Phone: 98765432
    HKID: AB123456(A)

    繁體中文:
    姓名：Chan Ka Yan
    手機：91234567
    身份證號碼：C123456(7)

    简体中文:
    客户：Lee Chi Wai
    电话：51234567
    证件号：D654321(8)
    """

    print("\n" + "-" * 70)
    print("【三语混合场景】原文:")
    print(text_mixed)

    entities = guardrail_tc.detect(text_mixed)
    print(f"\n检测到 {len(entities)} 个 PII 实体:")
    for e in entities:
        print(f"  • {e.entity_type}: '{e.text}'")

    safe_text = guardrail_tc.redact(text_mixed)
    print("\n脱敏后:")
    print(safe_text)

    return True


def test_traditional_chinese():
    """测试繁体中文模式 - 完整覆盖香港PII三语场景"""
    print("\n" + "=" * 70)
    print("繁体中文模式测试 (Traditional Chinese Mode)")
    print("=" * 70)

    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")

    # ========== 繁体中文测试用例 ==========
    test_cases = [
        # 电话场景
        ("手機號碼：91234567", "繁体-手機號碼"),
        ("聯絡電話：5678 1234", "繁体-聯絡電話"),
        ("電話：51234567", "繁体-電話"),
        ("致電：98765432", "繁体-致電"),
        ("熱線：51234567", "繁体-熱線"),

        # 身份证场景
        ("香港身份證：A123456(7)", "繁体-香港身份證"),
        ("身份證號碼：AB123456(A)", "繁体-身份證號碼"),
        ("證件號碼：C123456(8)", "繁体-證件號碼"),
        ("證件號：D654321(9)", "繁体-證件號"),
        ("身分證：E987654(0)", "繁体-身分證變體"),

        # 姓名场景
        ("客戶姓名：Wong Siu Ming", "繁体-客戶姓名"),
        ("聯絡人：Chan Ka Yan", "繁体-聯絡人"),
        ("顧客：Lee Chi Wai", "繁体-顧客"),
        ("持有人：Cheung Ka Keung", "繁体-持有人"),

        # 混合场景
        ("聯絡方式：電話5678 1234，HKID: AB123456(A)", "繁体-混合聯絡方式"),
        ("客戶：Wong Yan Yee，手機：91234567，身份證：A123456(7)", "繁体-完整客戶信息"),

        # 英文关键词在繁体模式
        ("Mobile: 91234567", "繁体模式-英文Mobile"),
        ("Tel: 51234567", "繁体模式-英文Tel"),
        ("HKID: A123456(7)", "繁体模式-英文HKID"),
        ("Name: Chan Tai Man", "繁体模式-英文Name"),
    ]

    passed = 0
    failed = 0

    print("\n繁体中文测试用例:")
    for text, desc in test_cases:
        entities = guardrail_tc.detect(text)
        safe = guardrail_tc.redact(text)

        # 检查是否检测到至少一个实体
        if entities:
            passed += 1
            print(f"✓ [{desc}] 检测到 {len(entities)} 个实体")
            print(f"  原文: {text}")
            print(f"  脱敏: {safe}")
        else:
            failed += 1
            print(f"✗ [{desc}] 未检测到实体")
            print(f"  原文: {text}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_universal_guardrail():
    """测试通用Guardrail - 自动语言检测与三语场景"""
    print("\n" + "=" * 70)
    print("UniversalPIIGuardrail 测试（自动语言检测 + 简体/繁体/英文）")
    print("=" * 70)

    guardrail = UniversalPIIGuardrail()

    test_cases = [
        # ========== 简体中文场景 ==========
        ("大陆手机13812345678", "simplified", "CN_PHONE_NUMBER"),
        ("联系电话：91234567", "simplified", "HK_PHONE_NUMBER"),
        ("香港身份证：A123456(7)", "simplified", "HK_ID_CARD"),
        ("客户：Wong Yan Yee", "simplified", "HK_NAME"),
        ("客户张三，手机13812345678，身份证110101199001011234", "simplified", "CN_ID_CARD"),

        # ========== 繁体中文场景 ==========
        ("香港手機91234567", "traditional", "HK_PHONE_NUMBER"),
        ("聯絡電話：5678 1234", "traditional", "HK_PHONE_NUMBER"),
        ("身份證AB123456(A)", "traditional", "HK_ID_CARD"),
        ("香港身份證：C123456(7)", "traditional", "HK_ID_CARD"),
        ("客戶姓名：Chan Tai Man", "traditional", "HK_NAME"),
        ("聯絡人：Lee Chi Wai，手機：91234567", "traditional", "HK_PHONE_NUMBER"),

        # ========== 英文场景 ==========
        ("Phone: 91234567", "english", "HK_PHONE_NUMBER"),
        ("Mobile: 98765432, HKID: A123456(7)", "english", "HK_ID_CARD"),
        ("Name: Wong Siu Ming", "english", "HK_NAME"),
        ("Tel: 51234567, ID Card: AB123456(A)", "english", "HK_ID_CARD"),
        ("Contact Person: Chan Ka Yan, Telephone: 61234567", "english", "HK_NAME"),

        # ========== 混合场景 ==========
        ("客户Customer：Wong Yan Yee，电话Tel：91234567", "simplified", "HK_NAME"),
        ("客戶Name：Chan Tai Man，手機Mobile：98765432", "traditional", "HK_NAME"),
    ]

    passed = 0
    failed = 0

    print("\n自动语言检测与PII识别测试:")
    for text, expected_script, expected_entity in test_cases:
        script = guardrail._detect_script(text)
        entities = guardrail.detect(text)
        safe = guardrail.redact(text)

        # 检查语言检测
        script_correct = script == expected_script

        # 检查实体检测
        entity_detected = any(e.entity_type == expected_entity for e in entities)

        if script_correct and entity_detected:
            passed += 1
            status = "✓"
        else:
            failed += 1
            status = "✗"

        print(f"\n{status} 原文: {text}")
        print(f"   语言检测: {script} (期望: {expected_script}) {'✓' if script_correct else '✗'}")
        print(f"   实体检测: {[e.entity_type for e in entities]}")
        print(f"   期望实体: {expected_entity} {'✓' if entity_detected else '✗'}")
        print(f"   脱敏: {safe}")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_edge_cases():
    """测试边界情况 - 简体、繁体、英文三语边界场景"""
    print("\n" + "=" * 70)
    print("边界情况测试 (简体/繁体/英文)")
    print("=" * 70)

    guardrail_sc = ChinesePIIGuardrail(script_type="simplified")
    guardrail_tc = ChinesePIIGuardrail(script_type="traditional")
    guardrail_en = ChinesePIIGuardrail(script_type="simplified")

    passed = 0
    failed = 0

    # ========== 香港电话边界情况 ==========
    print("\n--- 香港电话边界情况 ---")
    not_hk_phone = [
        # 错误前缀
        ("12345678", "1开头不应识别"),
        ("01234567", "0开头不应识别"),
        ("41234567", "4开头不应识别"),
        # 错误长度
        ("2345678", "7位数字"),
        ("512345678", "9位数字"),
        ("5123456", "7位数字"),
        # 大陆手机
        ("13812345678", "大陆11位手机号"),
        ("+8613812345678", "大陆手机国际格式"),
        # 特殊格式
        ("5-123-4567", "连字符分隔"),
        ("(5)1234567", "带括号"),
    ]

    for text, desc in not_hk_phone:
        entities = guardrail_sc.detect(text)
        hk_phones = [e for e in entities if e.entity_type == "HK_PHONE_NUMBER"]
        if not hk_phones:
            passed += 1
            print(f"✓ [{desc}] '{text}' 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' 错误识别为香港电话: {hk_phones[0].text}")

    # ========== 香港身份证边界情况 ==========
    print("\n--- 香港身份证边界情况 ---")
    not_hk_id = [
        # 格式错误
        ("A1234567", "无括号"),
        ("A123456(10)", "括号内两位数"),
        ("123456(7)", "无字母前缀"),
        ("ABC123456(7)", "三字母前缀"),
        ("A12345(7)", "5位数字"),
        ("A1234567(7)", "7位数字"),
        # 特殊字符
        ("A-123456-(7)", "连字符分隔"),
        ("A123456[7]", "方括号"),
        ("A123456{7}", "花括号"),
        # 大陆身份证
        ("110101199001011234", "大陆18位身份证"),
        ("110101900101123", "大陆15位身份证"),
    ]

    for text, desc in not_hk_id:
        entities = guardrail_sc.detect(text)
        hk_ids = [e for e in entities if e.entity_type == "HK_ID_CARD"]
        if not hk_ids:
            passed += 1
            print(f"✓ [{desc}] '{text}' 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' 错误识别为香港身份证: {hk_ids[0].text}")

    # ========== 香港姓名边界情况 ==========
    print("\n--- 香港姓名边界情况 ---")
    not_hk_name = [
        # 无上下文
        ("Wong went to the store", "只有姓氏无上下文"),
        ("Chan is a student", "只有姓氏无上下文"),
        # 非香港常见姓氏
        ("Name: John Smith", "非香港英文姓名"),
        ("Name: Michael Johnson", "非香港英文姓名"),
        ("Contact: Peter Brown", "非香港英文姓名"),
        # 中文姓名
        ("Name: 张三", "中文姓名"),
        ("Contact: 李四", "中文联系人"),
        # 单字/不完整
        ("Name: W", "单字母"),
        ("Name: Wong", "只有姓氏"),
    ]

    for text, desc in not_hk_name:
        entities = guardrail_en.detect(text)
        hk_names = [e for e in entities if e.entity_type == "HK_NAME"]
        if not hk_names:
            passed += 1
            print(f"✓ [{desc}] '{text}' 正确不识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' 错误识别为香港姓名: {hk_names[0].text}")

    # ========== 繁体中文特殊边界 ==========
    print("\n--- 繁体中文特殊边界 ---")
    tc_edge_cases = [
        ("手機：12345678", "繁体-1开头不应识别"),
        ("身份證：123456(7)", "繁体-无字母前缀"),
        ("聯絡人：John Smith", "繁体-非香港英文姓名"),
    ]

    for text, desc in tc_edge_cases:
        entities = guardrail_tc.detect(text)
        # 检查是否没有检测到预期的香港PII
        hk_entities = [e for e in entities if e.entity_type.startswith("HK_")]
        if not hk_entities:
            passed += 1
            print(f"✓ [{desc}] '{text}' 正确不识别香港PII")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text}' 错误识别: {[e.entity_type for e in hk_entities]}")

    # ========== 特殊字符与格式边界 ==========
    print("\n--- 特殊字符与格式边界 ---")
    special_cases = [
        ("Mobile\t:\t91234567", "制表符分隔"),
        ("Name:\nWong Yan Yee", "换行分隔"),
        ("Tel:  91234567", "多个空格"),
        ("Mobile:91234567", "无空格"),
        ("[Mobile: 91234567]", "方括号包围"),
        ("(Tel: 51234567)", "圆括号包围"),
    ]

    for text, desc in special_cases:
        entities = guardrail_en.detect(text)
        # 应该能检测到
        if entities and any(e.entity_type == "HK_PHONE_NUMBER" for e in entities):
            passed += 1
            print(f"✓ [{desc}] '{text[:30]}...' 正确识别")
        else:
            failed += 1
            print(f"✗ [{desc}] '{text[:30]}...' 未能识别")

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return failed == 0


def test_real_world_scenarios():
    """测试真实场景 - 模拟实际业务文档"""
    print("\n" + "=" * 70)
    print("真实场景测试 (Real-World Scenarios)")
    print("=" * 70)

    guardrail = UniversalPIIGuardrail()

    scenarios = [
        # ========== 银行开户场景 ==========
        {
            "name": "银行开户表格（繁体）",
            "text": """
            香港上海滙豐銀行有限公司
            開戶申請表

            個人資料:
            客戶姓名：Chan Tai Man
            香港身份證號碼：A123456(7)
            聯絡電話：91234567
            手機號碼：98765432
            電郵地址：test@hsbc.com.hk
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER", "HK_PHONE_NUMBER", "EMAIL_ADDRESS"]
        },

        # ========== 客服对话场景（简体） ==========
        {
            "name": "客服对话（简体）",
            "text": """
            客服：您好，请问有什么可以帮您？
            客户：我要查询我的账户。
            客服：请提供您的姓名和身份证号。
            客户：姓名 Wong Yan Yee，香港身份证 AB123456(A)，电话 91234567。
            客服：好的，请稍等。
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER"]
        },

        # ========== 英文商务邮件 ==========
        {
            "name": "英文商务邮件",
            "text": """
            Subject: Client Information Update

            Dear Team,

            Please find the updated client information below:

            Client Name: Lee Chi Wai
            HKID: C123456(7)
            Mobile: 91234567
            Office Phone: 51234567
            Email: client@example.com

            Best regards,
            Sales Team
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER", "HK_PHONE_NUMBER", "EMAIL_ADDRESS"]
        },

        # ========== 混合语言合同 ==========
        {
            "name": "混合语言合同",
            "text": """
            SERVICE AGREEMENT / 服務協議

            Party A (甲方): ABC Company Limited
            Party B (乙方): Wong Siu Ming (陳小明)

            Contact Information / 聯絡資料:
            - Name/姓名: Chan Ka Yan
            - HKID/身份證: D654321(8)
            - Phone/電話: Mobile 91234567, Office 51234567
            - Address/地址: Room 123, 1/F, Building A, Hong Kong

            Date/日期: 2024-01-15
            """,
            "expected_entities": ["HK_NAME", "HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER", "HK_PHONE_NUMBER"]
        },

        # ========== 医院登记场景 ==========
        {
            "name": "医院登记（繁体）",
            "text": """
            聖保祿醫院病人登記表

            病人姓名：Cheung Wai Man
            香港身份證：E987654(3)
            出生日期：1990-05-20
            聯絡電話：住宅 31234567，手機 91234567
            緊急聯絡人：Lam Chi Ming
            緊急聯絡電話：98765432

            病人簽署：_____________
            日期：2024-01-15
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER", "HK_PHONE_NUMBER", "HK_NAME", "HK_PHONE_NUMBER"]
        },

        # ========== 物流/快递单 ==========
        {
            "name": "快递单（简体）",
            "text": """
            顺丰速运
            寄件人：Yip Tsz Chun
            电话：91234567
            身份证：F111111(6)

            收件人：张三
            电话：13812345678
            地址：北京市朝阳区xxx
            """,
            "expected_entities": ["HK_NAME", "HK_PHONE_NUMBER", "HK_ID_CARD", "CN_PHONE_NUMBER"]
        },

        # ========== 酒店预订确认 ==========
        {
            "name": "酒店预订（英文）",
            "text": """
            Booking Confirmation - The Peninsula Hong Kong

            Guest Information:
            Name: Ho Ka Yan
            Passport/HKID: G222222(7)
            Contact: Mobile 91234567

            Reservation Details:
            Check-in: 2024-02-01
            Check-out: 2024-02-03
            Room Type: Deluxe Harbour View

            Confirmation Number: HK12345678
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER"]
        },

        # ========== 保险理赔申请 ==========
        {
            "name": "保险理赔（繁体+英文）",
            "text": """
            友邦保險索償申請表 AIA Claims Form

            投保人資料 Policyholder Information:
            姓名 Name: Ng Ka Ming
            香港身份證 HKID: H333333(4)
            聯絡電話 Contact: 住宅 Home 31234567 / 手機 Mobile 91234567

            受保人資料 Insured Person:
            姓名 Name: Chan Siu Ling
            身份證 ID: I444444(5)

            索償日期 Date of Claim: 2024-01-10
            """,
            "expected_entities": ["HK_NAME", "HK_ID_CARD", "HK_PHONE_NUMBER", "HK_PHONE_NUMBER", "HK_NAME", "HK_ID_CARD"]
        },
    ]

    passed = 0
    failed = 0

    for scenario in scenarios:
        print(f"\n--- {scenario['name']} ---")
        text = scenario["text"]
        expected = scenario["expected_entities"]

        entities = guardrail.detect(text)
        detected_types = [e.entity_type for e in entities]

        # 检查是否检测到所有期望的实体类型
        missing = [e for e in expected if e not in detected_types]
        extra = [e for e in detected_types if e not in expected and e.startswith("HK_")]

        if not missing:
            passed += 1
            print(f"✓ 通过 - 检测到 {len(entities)} 个实体")
            print(f"  实体类型: {detected_types}")
        else:
            failed += 1
            print(f"✗ 失败 - 缺少期望实体: {missing}")
            print(f"  检测到: {detected_types}")
            print(f"  期望: {expected}")

        if extra:
            print(f"  ⚠ 额外检测到: {extra}")

        # 显示脱敏结果（前100字符）
        safe_text = guardrail.redact(text)
        preview = safe_text.replace('\n', ' ')[:100]
        print(f"  脱敏预览: {preview}...")

    print(f"\n结果: {passed}/{len(scenarios)} 通过, {failed} 失败")
    return failed == 0


def test_performance():
    """简单性能测试"""
    print("\n" + "=" * 70)
    print("性能测试 (Performance Test)")
    print("=" * 70)

    import time
    guardrail = ChinesePIIGuardrail()

    # 测试文本
    test_text = """
    客户信息登记表

    客户：Wong Yan Yee
    香港身份证：A123456(7)
    电话：91234567

    联系人：Chan Tai Man
    电话：98765432
    ID: B654321(0)
    """

    # 预热
    for _ in range(5):
        guardrail.detect(test_text)

    # 正式测试
    iterations = 100
    start = time.time()
    for _ in range(iterations):
        guardrail.detect(test_text)
    elapsed = time.time() - start

    avg_time = (elapsed / iterations) * 1000  # 毫秒

    print(f"\n测试配置:")
    print(f"  迭代次数: {iterations}")
    print(f"  总耗时: {elapsed:.3f} 秒")
    print(f"  平均每次: {avg_time:.2f} ms")

    # 性能阈值（宽松）
    if avg_time < 100:  # 100ms以内
        print(f"✓ 性能良好 (< 100ms)")
        return True
    elif avg_time < 500:  # 500ms以内
        print(f"⚠ 性能一般 ({avg_time:.2f}ms)")
        return True
    else:
        print(f"✗ 性能较差 (> 500ms)")
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 70)
    print("香港 PII 识别器完整测试套件 (简体/繁体/英文三语覆盖)")
    print("=" * 70)
    print("\n测试模块:")
    print("  1. 香港英文姓名识别 - 简/繁/英三语上下文")
    print("  2. 香港电话识别 - 多种格式+三语上下文")
    print("  3. 香港身份证识别 - 单/双字母+三语上下文")
    print("  4. 脱敏功能 - 三语占位符")
    print("  5. 大陆区分 - 香港vs大陆PII识别")
    print("  6. 混合内容 - 三语混合场景")
    print("  7. 繁体中文模式 - Traditional Chinese专项")
    print("  8. 通用Guardrail - 自动语言检测")
    print("  9. 边界情况 - 负例+特殊字符")
    print("  10. 真实场景 - 模拟业务文档")
    print("  11. 性能测试 - 响应时间")

    results = {
        "1. 香港英文姓名识别": test_hk_name(),
        "2. 香港电话识别": test_hk_phone_number(),
        "3. 香港身份证识别": test_hk_id_card(),
        "4. 脱敏功能": test_redaction(),
        "5. 大陆区分": test_distinction_from_mainland(),
        "6. 混合内容": test_mixed_content(),
        "7. 繁体中文模式": test_traditional_chinese(),
        "8. 通用Guardrail": test_universal_guardrail(),
        "9. 边界情况": test_edge_cases(),
        "10. 真实场景": test_real_world_scenarios(),
        "11. 性能测试": test_performance(),
    }

    print("\n" + "=" * 70)
    print("测试汇总")
    print("=" * 70)

    for name, passed in results.items():
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{status} - {name}")

    total_passed = sum(1 for v in results.values() if v)
    total_tests = len(results)
    pass_rate = (total_passed / total_tests) * 100

    print(f"\n总计: {total_passed}/{total_tests} 通过 ({pass_rate:.1f}%)")

    if total_passed == total_tests:
        print("\n🎉 所有测试通过！")
    elif pass_rate >= 80:
        print("\n⚠ 大部分测试通过，有少量失败")
    else:
        print("\n❌ 测试失败较多，需要检查")

    return all(results.values())


if __name__ == "__main__":
    run_all_tests()
