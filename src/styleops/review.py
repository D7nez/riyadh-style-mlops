"""Deterministic warning heuristics, NOT an entailment model or factual correctness certificate."""
import re
from collections import Counter
from decimal import Decimal
from langsmith import traceable
BANNED=["وفي النهاية","وأخيراً","وفي الختام","وبالتالي","وبناءً على ذلك"]
NUMBER=r"\d+(?:[.,]\d+)*"
QUALIFIERS={"more_than":["أكثر من","اكثر من","ما يزيد على","يزيد عن"],"less_than":["أقل من","اقل من","دون"],"approximate":["نحو","حوالي","قرابة","تقريبًا","تقريبا"],"at_least":["على الأقل","على الاقل","لا يقل عن"],"at_most":["على الأكثر","على الاكثر","لا يزيد على","لا يتجاوز","حتى"]}

def normalized(text):
    return re.sub(r"[\u064b-\u065f\u0670ـ]","",text).translate(str.maketrans("٠١٢٣٤٥٦٧٨٩٫٬","0123456789.,"))

@traceable(name="validate_style")
def style_issues(text, source=None):
    issues=[]
    if re.search(r"[a-zA-Z]",text) and (source is None or set(re.findall(r"[a-zA-Z]+",text))-set(re.findall(r"[a-zA-Z]+",source))): issues.append("latin_characters")
    if text.count("من خلال")>1: issues.append("repeated_min_khilal")
    # Arabic comma is not a sentence boundary; decimal points are not boundaries either.
    first=re.split(r"(?<!\d)\.(?!\d)|[!?؟\n]",text.strip(),maxsplit=1)[0]
    if len(first.split())>20: issues.append("opening_over_20_words")
    if any(w in text for w in BANNED): issues.append("banned_phrase")
    if any(len(re.findall(r"(?<!\w)حيث(?!\w)",p))>1 for p in text.split("\n\n")): issues.append("repeated_hayth")
    if re.search(r"\*\*|^\s*#{1,6}\s",text,re.M): issues.append("markdown_formatting")
    return issues

def _number_key(value):
    value=re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))","",value)
    try: return str(Decimal(value).normalize())
    except Exception: return value

def number_claims(text):
    text=normalized(text);claims=[]
    for match in re.finditer(NUMBER,text):
        prefix=text[max(0,match.start()-30):match.start()].rstrip()
        suffix=text[match.end():match.end()+35]
        qualifier="exact"
        for category,phrases in QUALIFIERS.items():
            if any(prefix.endswith(phrase) or category in {"at_least","at_most"} and re.match(r"^\s*(?:[أ-ي]+\s+){0,2}"+re.escape(phrase),suffix) for phrase in phrases): qualifier=category;break
        percent=bool(re.match(r"\s*(?:%|٪|بالمئة|بالمائة)",suffix))
        claims.append((_number_key(match.group()),qualifier,"percent" if percent else "number"))
    return claims

def numbers(text): return {claim[0] for claim in number_claims(text)}

def factual_metrics(source,output):
    expected=numbers(source);actual=numbers(output)
    return {"number_recall":len(expected & actual)/len(expected) if expected else 1.0,"new_number_count":len(actual-expected)}

def factual_warnings(source,output):
    s=normalized(source);o=normalized(output);issues=[]
    sc=Counter(number_claims(source));oc=Counter(number_claims(output))
    for number in numbers(source) & numbers(output):
        left=Counter({(q,u):c for (n,q,u),c in sc.items() if n==number})
        right=Counter({(q,u):c for (n,q,u),c in oc.items() if n==number})
        # Counts/repetition alone are not treated as quantity changes.
        if set(left)!=set(right): issues.append("number_qualifier_or_percent_changed:"+number)
    metrics=factual_metrics(source,output)
    if metrics["number_recall"]<1: issues.append("source_numbers_missing")
    if metrics["new_number_count"]: issues.append("new_numbers_added")
    groups={
      "unsupported_authority_attribution":r"بدعم|برعاية|بتوجيه|توجيهات|القيادة الرشيدة|خادم الحرمين|ولي العهد",
      "unsupported_partnership":r"شركاء|شراكة|بالتعاون مع|بالتنسيق مع",
      "unsupported_named_location":r"الرياض|جدة|الدمام|مكة|المدينة المنورة",
      "unsupported_superlative":r"ضخمة|الأكبر|غير مسبوق|الرائدة|عالمية",
    }
    for code,pattern in groups.items():
        added={m.group() for m in re.finditer(pattern,o)}-{m.group() for m in re.finditer(pattern,s)}
        if added: issues.append(code)
    if re.search(r"تعتزم|تخطط|مقترح|تدرس|من المتوقع|قد يتم",s) and re.search(r"تم افتتاح|افتتحت|نفذت|أنجزت|اكتمل|اعتمدت",o):
        issues.append("planned_to_completed_possible_change")
    for phrase,positive in [("لم يبدأ","بدأ"),("لم تعتمد","اعتمدت"),("لا تشمل","تشمل")]:
        if phrase in s and positive in o and phrase not in o: issues.append("negation_possible_change")
    return sorted(set(issues))

def case_checks(case,output):
    missing=[phrase for phrase in case.get("required_phrases",[]) if normalized(phrase) not in normalized(output)]
    forbidden=[phrase for phrase in case.get("forbidden_phrases",[]) if normalized(phrase) in normalized(output)]
    return {"missing_required_phrases":missing,"forbidden_phrases_found":forbidden}
