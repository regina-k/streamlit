"""Small formatting helpers shared by Streamlit modules."""


def format_price_kor(eok: float) -> str:
    """Format an amount expressed in eok won as Korean money text."""
    value = float(eok or 0)
    sign = "-" if value < 0 else ""
    total_man = round(abs(value) * 10000)
    eok_part, man_part = divmod(total_man, 10000)

    if eok_part and man_part:
        return f"{sign}{eok_part:,}억 {man_part:,}만 원"
    if eok_part:
        return f"{sign}{eok_part:,}억 원"
    return f"{sign}{man_part:,}만 원"


def man_to_eok_str(man: int | float) -> str:
    """Format an amount expressed in manwon as Korean money text."""
    return format_price_kor(float(man or 0) / 10000)
