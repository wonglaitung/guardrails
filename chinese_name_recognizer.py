"""
中文姓名识别器

提供多种中文姓名识别方案：
1. 基于姓氏列表 + 规则
2. 基于 spaCy 中文 NER + 姓氏过滤
3. 混合方案（推荐）
"""

import re
from typing import List, Optional, Tuple, Set
from dataclasses import dataclass


# 中国常见姓氏（前100大姓，覆盖约85%人口）
COMMON_SURNAMES = set('王李张刘陈杨赵黄周吴徐孙胡朱高林何郭马罗梁宋郑谢韩唐冯于董萧程曹袁邓许傅沈曾彭吕苏卢蒋蔡贾丁魏薛叶阎余潘杜戴夏钟汪田任姜范方石姚谭廖邹熊金陆郝孔白崔康毛邱秦江史顾侯邵孟龙万段漕钱汤尹黎易常武乔贺赖龚文')

# 复姓
COMPOUND_SURNAMES = [
    '欧阳', '上官', '司马', '诸葛', '东方', '皇甫', '尉迟', '公孙', '令狐', '宇文',
    '长孙', '慕容', '司徒', '南宫', '独孤', '百里', '端木', '轩辕', '赫连', '澹台',
]

@dataclass
class NameMatch:
    """姓名匹配结果"""
    text: str
    start: int
    end: int
    score: float
    surname: str
    given_name: str


class ChineseNameRecognizer:
    """
    中文姓名识别器

    使用方法:
        recognizer = ChineseNameRecognizer()

        names = recognizer.recognize("联系人：张伟，电话13912345678")
        # [NameMatch(text='张伟', surname='张', given_name='伟', score=0.9)]
    """

    def __init__(self, use_spacy: bool = True, min_score: float = 0.5):
        """
        初始化

        Args:
            use_spacy: 是否使用 spaCy NER 辅助
            min_score: 最小置信度阈值
        """
        self.use_spacy = use_spacy
        self.min_score = min_score
        self.nlp = None

        if use_spacy:
            try:
                import spacy
                self.nlp = spacy.load('zh_core_web_sm')
            except Exception:
                self.nlp = None

    def recognize(self, text: str) -> List[NameMatch]:
        """
        识别文本中的中文姓名

        Args:
            text: 待识别文本

        Returns:
            识别到的姓名列表
        """
        results = []

        # 方案1：基于规则识别
        rule_results = self._recognize_by_rules(text)
        results.extend(rule_results)

        # 方案2：spaCy NER + 姓氏过滤
        if self.nlp:
            spacy_results = self._recognize_by_spacy(text)
            # 合并结果，去重
            results = self._merge_results(results, spacy_results)

        # 过滤低分结果
        results = [r for r in results if r.score >= self.min_score]

        return results

    def _recognize_by_rules(self, text: str) -> List[NameMatch]:
        """基于规则识别姓名"""
        results = []

        # 模式1：姓名上下文关键词
        name_patterns = [
            # "叫/是/姓名" + 姓名
            r'(?:叫|是|姓名|名字|联系人|联系|客户|用户|本人|持卡人)[:：]?\s*([一-龥]{2,4})',
            # 姓名 + "的" + 其他
            r'([一-龥]{2,3})的(?:手机|电话|邮箱|身份证|银行卡)',
            # 姓氏开头的2-4字姓名
            r'(?<![一-龥])([一-龥]{2,4})(?![一-龥])',
        ]

        for pattern in name_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                candidate = match.group(1)
                start, end = match.start(1), match.end(1)

                # 验证是否为有效姓名
                name_match = self._validate_name(candidate, start, end)
                if name_match:
                    results.append(name_match)

        return results

    def _recognize_by_spacy(self, text: str) -> List[NameMatch]:
        """使用 spaCy NER 识别"""
        results = []

        try:
            doc = self.nlp(text)
            for ent in doc.ents:
                if ent.label_ == 'PERSON':
                    candidate = ent.text
                    start, end = ent.start_char, ent.end_char

                    # 姓氏过滤
                    name_match = self._validate_name(candidate, start, end)
                    if name_match:
                        results.append(name_match)
        except Exception:
            pass

        return results

    def _validate_name(self, candidate: str, start: int, end: int) -> Optional[NameMatch]:
        """
        验证候选字符串是否为有效中文姓名

        有效姓名条件：
        1. 长度 2-4 个汉字
        2. 以常见姓氏开头
        3. 不包含常见非姓名词汇
        """
        if not candidate:
            return None

        # 长度检查
        if len(candidate) < 2 or len(candidate) > 4:
            return None

        # 必须全是汉字
        if not all('\u4e00' <= c <= '\u9fff' for c in candidate):
            return None

        # 检查姓氏
        surname = None
        given_name = None

        # 检查复姓
        for cs in COMPOUND_SURNAMES:
            if candidate.startswith(cs):
                surname = cs
                given_name = candidate[len(cs):]
                break

        # 检查单姓
        if not surname:
            first_char = candidate[0]
            if first_char in COMMON_SURNAMES:
                surname = first_char
                given_name = candidate[1:]

        if not surname:
            return None

        # 过滤常见误报词汇
        false_positives = {
            '手机号', '电话号', '身份证', '银行卡', '邮箱地', '联系方',
            '公司名', '产品名', '用户名', '账号', '账户',
            '北京市', '上海市', '广州市', '深圳市',  # 城市名
            '周一', '周二', '周三', '周四', '周五', '周六', '周日',  # 星期
            '一月', '二月', '三月', '四月', '五月', '六月',  # 月份
        }

        if candidate in false_positives:
            return None

        # 计算置信度
        score = self._calculate_score(candidate, surname, given_name)

        return NameMatch(
            text=candidate,
            start=start,
            end=end,
            score=score,
            surname=surname,
            given_name=given_name
        )

    def _calculate_score(self, candidate: str, surname: str, given_name: str) -> float:
        """
        计算姓名置信度

        评分规则：
        - 基础分：0.7
        - 姓氏在常见姓氏中：+0.1
        - 名字长度 1-2 字：+0.1
        - 名字不包含罕见字：+0.05
        - 被 spaCy 识别为人名：+0.1（在 merge 时处理）
        """
        score = 0.7

        # 常见姓氏加分
        if surname in COMMON_SURNAMES or surname in COMPOUND_SURNAMES:
            score += 0.1

        # 名字长度合理
        if given_name and 1 <= len(given_name) <= 2:
            score += 0.1

        # 名字不含罕见字（简单判断）
        common_chars = set('伟芳娜敏静丽强磊军洋勇艳杰娟涛明超秀霞平刚桂英兰华建国文辉斌波宇红梅玲鹏峰毅浩清云翔林海天山风龙飞')
        if given_name and all(c in common_chars for c in given_name):
            score += 0.05

        return min(score, 1.0)

    def _merge_results(self, rule_results: List[NameMatch], spacy_results: List[NameMatch]) -> List[NameMatch]:
        """合并规则和 spaCy 结果"""
        # 使用位置作为唯一标识
        seen = {}
        for r in rule_results:
            seen[(r.start, r.end)] = r

        for r in spacy_results:
            key = (r.start, r.end)
            if key in seen:
                # 如果重叠，选择分数更高的
                if r.score > seen[key].score:
                    seen[key] = r
            else:
                # spaCy 独有结果，加分
                r.score = min(r.score + 0.1, 1.0)
                seen[key] = r

        return list(seen.values())


def create_name_recognizer(use_spacy: bool = True) -> ChineseNameRecognizer:
    """创建中文姓名识别器"""
    return ChineseNameRecognizer(use_spacy=use_spacy)


# 便捷函数
def extract_chinese_names(text: str) -> List[str]:
    """
    快速提取文本中的中文姓名

    使用方法:
        names = extract_chinese_names("联系人：张伟，电话13912345678")
        # ['张伟']
    """
    recognizer = ChineseNameRecognizer()
    matches = recognizer.recognize(text)
    return [m.text for m in matches]


if __name__ == "__main__":
    print("=" * 70)
    print("中文姓名识别器测试")
    print("=" * 70)

    recognizer = ChineseNameRecognizer()

    test_cases = [
        "我的名字叫张伟，手机号是13812345678",
        "联系人：王经理，电话13987654321",
        "张三的手机号是13811112222",
        "李四的身份证号是110101199001011234",
        "请通知陈小明参加会议",
        "客户欧阳锋来电咨询",
        "用户姓名：司马光，电话：13900001111",
        "持卡人王小明，卡号：6222021234567890123",
        "手机号是13812345678",  # 无姓名
        "这是一段普通文本",  # 无姓名
    ]

    for text in test_cases:
        print(f"\n文本: {text}")
        names = recognizer.recognize(text)
        if names:
            for name in names:
                print(f"  → {name.text} (姓:{name.surname}, 名:{name.given_name}, 置信度:{name.score:.2f})")
        else:
            print("  → 未识别到姓名")
