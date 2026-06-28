from django import template


register = template.Library()


@register.filter
def score_out_of_10(value):
    try:
        score = float(value or 0)
    except (TypeError, ValueError):
        score = 0

    score = max(0, min(score, 100)) / 10

    if score.is_integer():
        return str(int(score))

    return f"{score:.1f}"
