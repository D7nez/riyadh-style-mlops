
import json
from styleops.review import factual_warnings,style_issues,case_checks,numbers
from styleops.config import ROOT

def test_reported_qwen_quantity_error():
    s="تعتزم المدينة تطوير 12 حديقة وزراعة 3000 شجرة."
    o="تستهدف أمانة منطقة الرياض تطوير 12 حديقة وزراعة أكثر من 3000 شجرة."
    flags=factual_warnings(s,o)
    assert any(f.startswith("number_qualifier_or_percent_changed") for f in flags)
    assert "unsupported_named_location" in flags

def test_reported_groq_partnership_error():
    flags=factual_warnings("تعتزم المدينة تطوير 12 حديقة.","بدعم القيادة الرشيدة تم التخطيط لتطوير 12 حديقة بالتعاون مع شركاء دوليين.")
    assert "unsupported_authority_attribution" in flags
    assert "unsupported_partnership" in flags

def test_comma_does_not_end_sentence():
    opening=" ".join(["كلمة"]*12)+"، "+" ".join(["أخرى"]*12)+"."
    assert "opening_over_20_words" in style_issues(opening)

def test_real_sentence_boundary_and_decimal():
    assert "opening_over_20_words" not in style_issues("نطور المدينة. "+" ".join(["كلمة"]*25))
    assert "opening_over_20_words" in style_issues(" ".join(["كلمة"]*12)+" 2.5 "+" ".join(["أخرى"]*12))

def test_qualifier_paraphrase_and_digit_normalization():
    assert not factual_warnings("نزرع نحو ٣٠٠٠ شجرة.","نزرع حوالي 3000 شجرة.")
    assert numbers("12.0") == numbers("١٢")

def test_percent_and_negation():
    assert any(f.startswith("number_qualifier_or_percent_changed") for f in factual_warnings("نسبة 12%", "عدد 12"))
    assert "negation_possible_change" in factual_warnings("لم يبدأ المشروع", "بدأ المشروع")

def test_supported_partners_are_not_flagged():
    assert "unsupported_partnership" not in factual_warnings("نعمل بالتعاون مع شركاء دوليين", "نعمل بالتعاون مع شركاء دوليين")

def test_constraints_and_corpus():
    rows=[json.loads(line) for line in (ROOT/"evaluation/quality_cases.jsonl").read_text().splitlines()]
    assert len(rows)==24 and len({r["id"] for r in rows})==24
    c=case_checks({"required_phrases":["جدة"],"forbidden_phrases":["الرياض"]},"الرياض")
    assert c["missing_required_phrases"]==["جدة"]
    assert c["forbidden_phrases_found"]==["الرياض"]

def test_original_latin_name_allowed():
    assert "latin_characters" not in style_issues("نختبر Python", "نختبر Python")
    assert "latin_characters" in style_issues("نختبر Excel", "نختبر Python")

def test_suffix_minimum_preserved():
    assert not factual_warnings("يشارك 20 متطوعا على الأقل", "يشارك على الأقل 20 متطوعا")
