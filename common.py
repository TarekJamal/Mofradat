import re

_DIAC = re.compile(r"[\u064B-\u065F\u0670\u06D6-\u06ED\u0640]")


def norm(s):
    """تطبيع النص العربي للبحث: حذف التشكيل وتوحيد الهمزات والياء والتاء المربوطة."""
    s = _DIAC.sub("", str(s or ""))
    s = re.sub("[إأآٱ]", "ا", s)
    return s.replace("ى", "ي").replace("ة", "ه").strip()
