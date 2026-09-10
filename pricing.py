"""ユーザー提供の料金表を構造化。金額の単位は円。"""

PLANS = {
    "visit-60": {"name": "出張60分", "minutes": 60, "price": 13000},
    "visit-90": {"name": "出張90分", "minutes": 90, "price": 16000},
    "visit-120": {"name": "出張120分", "minutes": 120, "price": 19000},
    "stay": {"name": "ステイ", "hours": "22:00–翌09:00", "price": 29000},
    "date": {"name": "デート2時間", "minutes": 120, "hours": "14:00–22:00", "price": 4000},
    "charter": {"name": "貸切", "price": 55000, "unit": "24時間", "multi_day_formula": "days * 50000 - days * 10000 (days >= 2)"},
}
OPTIONS = {
    "multiple-guests": {"name": "お客様が複数", "price": 0},
    "ejaculation": {"name": "拓也の射精", "price": 3000},
    "soft-m": {"name": "ソフトM受け", "price": 0},
    "hard-m": {"name": "ハードM受け", "price": 5000},
    "s": {"name": "拓也がS", "price": 3000},
    "equipment": {"name": "SM道具使用料", "price": 0},
}
PHOTOGRAPHY = {
    "none": {"name": "撮影なし", "price": 0},
    "body": {"name": "私的撮影・体のみ", "price": 3000},
    "anonymous": {"name": "私的撮影・サングラスまたは顔のわからないアングル", "price": 5000},
    "face": {"name": "私的撮影・顔出し", "price": None, "note": "設定外"},
    "commercial": {"name": "営利目的撮影", "price": None, "note": "予算に応じて相談"},
}
DISCOUNTS = {"repeater": 10, "younger": 10, "top": 20}
ASSUMPTIONS = [
    "割引は出張60/90/120分とステイの基本料だけに適用し、複数条件は加算する（最大40%）。原文で対象範囲・併用方法は未定義。",
    "延長は出張60/90/120分のみ、30分単位で指定。基本プランの自動変更・最安化はしない。",
    "撮影のみは通常出張プランのみ計算し、基本料を半額にした後に割引する。3Pコースの料金は未提供のため計算対象外。",
    "遠方料金は都内・近郊交通費の代わりに加算。往復時間は分入力、1000円/時で計算し1円未満を切り上げる。",
    "デートは単独2時間として扱い、リピーターかつ開始14:00〜20:00に制限。併用デートは対象外。",
    "オプションは各1回加算。税区分の記載がないため税額は追加しない。",
]

def catalog():
    return dict(currency="JPY", source="ユーザー提供の料金表", plans=PLANS,
                options=OPTIONS, photography=PHOTOGRAPHY, discounts_percent=DISCOUNTS,
                extension={"minutes": 30, "price": 3000},
                transport={"tokyo": 1000, "nearby": 2000,
                           "nearby_note": "浦安・横浜など原文の首都高圏内。地域は呼び出し側で判断。",
                           "remote": "往復交通費 + 往復所要時間（時間） * 1000、事前振込"},
                photography_note="120分以内一律。撮影のみは出張料金半額（3Pコース除く）。",
                assumptions=ASSUMPTIONS)

class InvalidQuote(ValueError):
    pass

def quote(data):
    if not isinstance(data, dict):
        raise InvalidQuote("JSONオブジェクトを送信してください。")
    allowed = {"plan", "extension_units", "days", "discounts", "options", "photography",
               "shooting_only", "region", "round_trip_fare", "round_trip_minutes", "start_time"}
    if set(data) - allowed:
        raise InvalidQuote("未対応のフィールド: " + ", ".join(sorted(set(data) - allowed)))

    def choice(key, values, default=None):
        value = data.get(key, default)
        if not isinstance(value, str) or value not in values:
            raise InvalidQuote(f"{key} は {', '.join(values)} から指定してください。")
        return value

    def integer(key, default, low=0, high=10000000):
        value = data.get(key, default)
        if type(value) is not int or not low <= value <= high:
            raise InvalidQuote(f"{key} は {low}〜{high} の整数で指定してください。")
        return value

    def selections(key, values):
        value = data.get(key, [])
        if not isinstance(value, list) or any(not isinstance(v, str) or v not in values for v in value):
            raise InvalidQuote(f"{key} は対応するIDの配列で指定してください。")
        if len(value) != len(set(value)):
            raise InvalidQuote(f"{key} に重複があります。")
        return value

    plan = choice("plan", PLANS)
    region = choice("region", ["tokyo", "nearby", "remote"])
    photo = choice("photography", PHOTOGRAPHY, "none")
    discounts = selections("discounts", DISCOUNTS)
    options = selections("options", OPTIONS)
    extension = integer("extension_units", 0, high=48)
    days = integer("days", 1, low=1, high=365)
    shooting = data.get("shooting_only", False)
    if type(shooting) is not bool:
        raise InvalidQuote("shooting_only は真偽値で指定してください。")
    visit = plan.startswith("visit-")
    if "days" in data and plan != "charter":
        raise InvalidQuote("days は貸切だけに指定できます。")
    if extension and not visit:
        raise InvalidQuote("延長は通常出張プランだけに指定できます。")
    if plan not in ("date", "stay") and not visit and discounts:
        raise InvalidQuote("貸切の割引は原文に規定がありません。")
    if plan == "date":
        if discounts != ["repeater"]:
            raise InvalidQuote("単独デートは discounts: [repeater] が必要です（料金の割引はしません）。")
        import re
        start = data.get("start_time")
        if not isinstance(start, str) or not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", start):
            raise InvalidQuote("start_time を HH:MM 形式で指定してください。")
        hour, minute = map(int, start.split(":"))
        if not 840 <= hour * 60 + minute <= 1200:
            raise InvalidQuote("2時間デートの開始は14:00〜20:00です。")
        if options or photo != "none":
            raise InvalidQuote("単独デートとオプションの併用は計算対象外です。")
    elif "start_time" in data:
        raise InvalidQuote("start_time はデートだけに指定できます。")
    if shooting and (not visit or photo == "none"):
        raise InvalidQuote("撮影のみは通常出張と撮影オプションを指定してください。")
    unresolved = []
    if photo != "none":
        if not visit or PLANS[plan]["minutes"] + extension * 30 > 120:
            unresolved.append("120分超または通常出張以外の撮影料金は要相談")
        if PHOTOGRAPHY[photo]["price"] is None:
            unresolved.append(PHOTOGRAPHY[photo]["name"] + ": " + PHOTOGRAPHY[photo]["note"])

    lines = []
    def add(name, amount):
        lines.append({"name": name, "amount": amount})

    base = PLANS[plan]["price"]
    if plan == "charter" and days >= 2:
        base = days * 50000 - days * 10000
    add(PLANS[plan]["name"], base)
    if shooting:
        add("撮影のみ基本料半額", -(base // 2))
        base //= 2
    rate = sum(DISCOUNTS[d] for d in discounts) if plan != "date" else 0
    if rate:
        add("基本料割引", -(base * rate // 100))
    if extension:
        add("延長", extension * 3000)
    for option in options:
        add(OPTIONS[option]["name"], OPTIONS[option]["price"])
    if photo != "none" and not unresolved:
        add(PHOTOGRAPHY[photo]["name"], PHOTOGRAPHY[photo]["price"])
    prepaid = 0
    if region == "remote":
        fare = integer("round_trip_fare", None)
        minutes = integer("round_trip_minutes", None, low=1)
        prepaid = fare + (minutes * 1000 + 59) // 60
        add("遠方料金（事前振込）", prepaid)
    else:
        if {"round_trip_fare", "round_trip_minutes"} & data.keys():
            raise InvalidQuote("往復交通費・時間は遠方だけに指定できます。")
        add("交通費", 1000 if region == "tokyo" else 2000)
    subtotal = sum(line["amount"] for line in lines)
    return dict(currency="JPY", status="requires_consultation" if unresolved else "estimated",
                total=None if unresolved else subtotal, known_subtotal=subtotal,
                prepaid_amount=prepaid, breakdown=lines, unresolved=unresolved,
                assumptions=ASSUMPTIONS)
