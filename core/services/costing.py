import os
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.utils import timezone

from cases.models import RealConsultationSession


DECIMAL_PLACES = Decimal("0.0001")
DISPLAY_PLACES = Decimal("0.01")


def decimal_from_env(name, default):
    raw_value = os.getenv(name, str(default)).strip()
    try:
        return Decimal(raw_value)
    except Exception:
        return Decimal(str(default))


def quantize_money(value):
    return Decimal(value).quantize(DISPLAY_PLACES, rounding=ROUND_HALF_UP)


def quantize_precise(value):
    return Decimal(value).quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class CostRates:
    realtime_text_input_per_1m: Decimal
    realtime_text_output_per_1m: Decimal
    realtime_audio_input_per_1m: Decimal
    realtime_audio_output_per_1m: Decimal
    transcription_per_minute: Decimal
    fallback_cost_per_live_consultation: Decimal
    live_pack_price: Decimal
    live_pack_credits: int
    stripe_percent: Decimal
    stripe_fixed_fee: Decimal

    @property
    def stripe_fee_for_live_pack(self):
        return (self.live_pack_price * self.stripe_percent) + self.stripe_fixed_fee

    @property
    def live_pack_net_revenue(self):
        return max(self.live_pack_price - self.stripe_fee_for_live_pack, Decimal("0"))

    @property
    def net_revenue_per_live_credit(self):
        if self.live_pack_credits <= 0:
            return Decimal("0")
        return self.live_pack_net_revenue / Decimal(self.live_pack_credits)


def get_cost_rates():
    live_pack_credits_raw = os.getenv("STRIPE_REAL_CONSULTATION_PACK_CREDITS", "5").strip()
    try:
        live_pack_credits = max(int(live_pack_credits_raw), 1)
    except ValueError:
        live_pack_credits = 5

    return CostRates(
        realtime_text_input_per_1m=decimal_from_env("COST_REALTIME_TEXT_INPUT_PER_1M", "4"),
        realtime_text_output_per_1m=decimal_from_env("COST_REALTIME_TEXT_OUTPUT_PER_1M", "24"),
        realtime_audio_input_per_1m=decimal_from_env("COST_REALTIME_AUDIO_INPUT_PER_1M", "32"),
        realtime_audio_output_per_1m=decimal_from_env("COST_REALTIME_AUDIO_OUTPUT_PER_1M", "64"),
        transcription_per_minute=decimal_from_env("COST_TRANSCRIPTION_PER_MINUTE", "0"),
        fallback_cost_per_live_consultation=decimal_from_env("COST_FALLBACK_PER_LIVE_CONSULTATION", "0.75"),
        live_pack_price=decimal_from_env("STRIPE_REAL_CONSULTATION_PACK_PRICE", "20"),
        live_pack_credits=live_pack_credits,
        stripe_percent=decimal_from_env("STRIPE_STANDARD_PERCENT", "0.015"),
        stripe_fixed_fee=decimal_from_env("STRIPE_STANDARD_FIXED_FEE", "0.20"),
    )


def estimate_session_cost(session, rates=None):
    rates = rates or get_cost_rates()

    input_tokens_used = Decimal(session.input_tokens_used or 0)
    output_tokens_used = Decimal(session.output_tokens_used or 0)
    transcription_seconds_used = Decimal(session.transcription_seconds_used or 0)

    text_input_cost = (input_tokens_used / Decimal("1000000")) * rates.realtime_text_input_per_1m
    text_output_cost = (output_tokens_used / Decimal("1000000")) * rates.realtime_text_output_per_1m
    transcription_cost = (transcription_seconds_used / Decimal("60")) * rates.transcription_per_minute

    measured_cost = text_input_cost + text_output_cost + transcription_cost

    # During early testing many sessions may not yet record token usage. This fallback protects pricing decisions.
    fallback_used = measured_cost == 0 and session.real_consultation_credit_charged
    estimated_total_cost = rates.fallback_cost_per_live_consultation if fallback_used else measured_cost

    net_revenue = rates.net_revenue_per_live_credit
    estimated_margin = net_revenue - estimated_total_cost

    return {
        "session": session,
        "clinical_case": session.clinical_case,
        "measured_cost": quantize_precise(measured_cost),
        "estimated_total_cost": quantize_precise(estimated_total_cost),
        "estimated_total_cost_display": quantize_money(estimated_total_cost),
        "net_revenue_display": quantize_money(net_revenue),
        "estimated_margin_display": quantize_money(estimated_margin),
        "estimated_margin": quantize_precise(estimated_margin),
        "fallback_used": fallback_used,
        "input_tokens_used": session.input_tokens_used or 0,
        "output_tokens_used": session.output_tokens_used or 0,
        "transcription_seconds_used": session.transcription_seconds_used or 0,
        "turn_count": session.turn_count or 0,
        "credit_charged": session.real_consultation_credit_charged,
        "status": session.status,
    }


def get_current_month_range():
    now = timezone.localtime(timezone.now())
    start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def build_user_cost_summary(user, limit=50):
    rates = get_cost_rates()
    month_start, month_end = get_current_month_range()

    sessions = (
        RealConsultationSession.objects.filter(user=user)
        .select_related("clinical_case")
        .order_by("-created_at")[:limit]
    )

    month_sessions = RealConsultationSession.objects.filter(
        user=user,
        created_at__gte=month_start,
        created_at__lt=month_end,
    ).select_related("clinical_case")

    session_rows = [estimate_session_cost(session, rates=rates) for session in sessions]
    month_rows = [estimate_session_cost(session, rates=rates) for session in month_sessions]

    total_month_cost = sum((row["estimated_total_cost"] for row in month_rows), Decimal("0"))
    charged_month_count = sum(1 for row in month_rows if row["credit_charged"])
    net_revenue_month = rates.net_revenue_per_live_credit * Decimal(charged_month_count)
    margin_month = net_revenue_month - total_month_cost

    average_cost = Decimal("0")
    if month_rows:
        average_cost = total_month_cost / Decimal(len(month_rows))

    return {
        "rates": rates,
        "session_rows": session_rows,
        "month_start": month_start,
        "month_end": month_end,
        "charged_month_count": charged_month_count,
        "month_session_count": len(month_rows),
        "total_month_cost": quantize_money(total_month_cost),
        "net_revenue_month": quantize_money(net_revenue_month),
        "margin_month": quantize_money(margin_month),
        "average_cost": quantize_money(average_cost),
        "live_pack_net_revenue": quantize_money(rates.live_pack_net_revenue),
        "net_revenue_per_live_credit": quantize_money(rates.net_revenue_per_live_credit),
        "stripe_fee_for_live_pack": quantize_money(rates.stripe_fee_for_live_pack),
    }
