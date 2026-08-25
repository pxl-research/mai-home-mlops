'''
Detecting current leaks (anomaly detection): water usage alone is sufficient.
- Isolation Forest on hourly usage vectors works well for unusual consumption patterns (e.g., sustained flow at 3 AM).
- The "at least one zero per day" heuristic is a clean rule: a slow drip keeps the meter ticking continuously, so no zero-hour within 24h is a strong leak signal. Water utilities actually use this in practice.
- You can combine both: isolation forest catches sudden high-flow events (burst pipe), zero-gap heuristic catches slow continuous leaks.

NOTE: 2 households per category (these are the household_id's) and should be selectable via dropdown in Grafana:
* single_be
* single_nl
* couple_be
* couple_nl
* family_be
* family_nl
'''
import pandas as pd
import numpy as np
import datetime
from dateutil.relativedelta import relativedelta
import holidays as holidays_lib


def _sample_leakage_volume():
    return round(max(1, np.random.normal(1.5, 0.5)))


def _build_vacation_days(date_range, vacation_probability, seed, country="be"):
    all_dates = sorted({dt.date() for dt in date_range})
    if not all_dates:
        return set(), set()

    years = {d.year for d in all_dates}
    if country.lower() == "nl":
        holidays_list = holidays_lib.Netherlands(years=years)
    else:
        holidays_list = holidays_lib.Belgium(years=years)

    date_set = set(all_dates)
    home_holiday_days = {d for d in all_dates if d in holidays_list}
    target = int(vacation_probability * len(all_dates))
    vacation_days = set()
    budget = max(0, target)

    if budget == 0:
        return vacation_days, home_holiday_days

    month_weight = {1: 0.3, 2: 0.4, 3: 0.6, 4: 1.2, 5: 0.7, 6: 1.5,
                    7: 3.0, 8: 3.0, 9: 1.2, 10: 0.5, 11: 0.3, 12: 0.6}

    rng = np.random.RandomState(seed if seed is not None else 0)

    max_attempts = 2000
    attempts = 0
    while budget > 0 and attempts < max_attempts:
        attempts += 1
        candidates = [d for d in all_dates if d not in vacation_days]
        if not candidates:
            break

        weights = np.array([month_weight[d.month] for d in candidates], dtype=float)
        for i, d in enumerate(candidates):
            if d.weekday() == 0 or d.weekday() == 4:
                weights[i] *= 1.8
            prev = d - datetime.timedelta(days=1)
            if prev in vacation_days or prev in home_holiday_days:
                weights[i] *= 2.5

        weights /= weights.sum()
        start = candidates[rng.choice(len(candidates), p=weights)]

        if start.weekday() in (1, 2):
            start = start - datetime.timedelta(days=start.weekday())

        length = int(rng.randint(5, 15))
        block = {start + datetime.timedelta(days=i) for i in range(length)} & date_set
        new_days = block - vacation_days
        if not new_days:
            continue

        if len(new_days) > budget + 14:
            continue

        vacation_days.update(new_days)
        budget -= len(new_days)

    return vacation_days, home_holiday_days


def _init_date_range(date_range, start_date_str, years):
    if date_range is None:
        start_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = start_date + relativedelta(years=years)
        date_range = pd.date_range(start=start_date, end=end_date, freq='h')[:-1]
    return date_range


def _determine_leak_start_dt(date_range, has_leakage_prob, history_df=None):
    """
    Determines if a persistent leakage occurs.

    If history_df is provided and indicates an ongoing leak, the leakage is carried over.
    Otherwise, a new leak start timestamp is selected probabilistically within date_range.
    """
    # 1. Check if history already has an active leakage state
    if history_df is not None and not history_df.empty:
        if 'is_leakage' in history_df.columns and history_df['is_leakage'].iloc[-1]:
            # Leakage was active at the end of history buffer; carry it forward
            return date_range[0]

    # 2. Sample new leakage start if probability triggers
    if has_leakage_prob > 0 and np.random.rand() < has_leakage_prob and len(date_range) > 0:
        leak_idx = np.random.randint(0, len(date_range))
        return date_range[leak_idx]

    return None


def _iter_hourly(
    date_range, anchor_date, vacation_days, home_holiday_days, leak_start_dt,
    weekday_profile, weekend_profile, weekday_activity_prob, weekend_activity_prob,
    softener_cycle, softener_offset, softener_hours, softener_volumes, softener_jitter,
    seasonal_amplitude, noise_fraction,
    extra_absence_check=None,
):
    softener_split = {}

    for dt in date_range:
        has_leakage = (leak_start_dt is not None) and (dt >= leak_start_dt)
        hour = dt.hour
        is_weekend = dt.dayofweek >= 5
        days_since_anchor = (dt.date() - anchor_date).days

        if softener_cycle > 0 and days_since_anchor % softener_cycle == softener_offset and hour in softener_hours:
            idx = softener_hours.index(hour)
            if idx == 0:
                jitter = np.random.randint(*softener_jitter)
                total = sum(softener_volumes) + jitter
                v0 = round(total * softener_volumes[0] / max(1, sum(softener_volumes)))
                softener_split[dt.date()] = (v0, total - v0)
            yield dt, softener_split[dt.date()][idx], has_leakage
            continue

        if dt.date() in vacation_days:
            yield dt, _sample_leakage_volume() if has_leakage else 0, has_leakage
            continue

        is_weekend_like = is_weekend or (dt.date() in home_holiday_days)
        prob_profile = weekend_activity_prob if is_weekend_like else weekday_activity_prob
        vol_profile = weekend_profile if is_weekend_like else weekday_profile

        is_active = np.random.rand() < prob_profile[hour]

        if extra_absence_check is not None and extra_absence_check(dt, is_weekend, hour):
            is_active = False

        if not is_active:
            yield dt, _sample_leakage_volume() if has_leakage else 0, has_leakage
        else:
            base_volume = vol_profile[hour]
            if base_volume == 0.0:
                yield dt, _sample_leakage_volume() if has_leakage else 0, has_leakage
            else:
                seasonal_factor = 1.0 + seasonal_amplitude * np.cos(2 * np.pi * (dt.month - 7) / 12)
                volume = base_volume * seasonal_factor
                noise = np.random.normal(0, max(0.5, volume * noise_fraction))
                yield dt, round(max(1, volume + noise)), has_leakage


def _to_dataframe(iter_fn, household_id, stream):
    if stream:
        return (pd.DataFrame({
            'timestamp': [dt],
            'volume_liter': [vol],
            'household_id': household_id,
            'is_leakage': [is_leak]
        }) for dt, vol, is_leak in iter_fn())

    timestamps, volumes, leaks = [], [], []
    for dt, vol, is_leak in iter_fn():
        timestamps.append(dt)
        volumes.append(vol)
        leaks.append(is_leak)

    return pd.DataFrame({
        'timestamp': timestamps,
        'volume_liter': volumes,
        'household_id': household_id,
        'is_leakage': leaks
    })


def generate_couple_water_consumption(
    date_range=None, start_date_str="2024-01-01", years=2, seed=42,
    household_id="couple_be", vacation_probability=0.05, has_leakage_prob=0.0,
    stream=False, country="be", history_buffer_df=None
):
    date_range = _init_date_range(date_range, start_date_str, years)
    if seed is not None:
        np.random.seed(seed)

    anchor_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    vacation_days, home_holiday_days = _build_vacation_days(date_range, vacation_probability, seed, country)
    leak_start_dt = _determine_leak_start_dt(date_range, has_leakage_prob, history_buffer_df)

    if country.lower() == "nl":
        weekday_profile = {
            0: 1.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
            6: 4.0, 7: 5.0, 8: 4.0, 9: 1.5, 10: 1.5, 11: 1.5,
            12: 2.5, 13: 1.5, 14: 1.5, 15: 2.0, 16: 4.5, 17: 8.0,
            18: 6.5, 19: 5.0, 20: 3.5, 21: 2.5, 22: 2.0, 23: 1.0
        }
        weekday_activity_prob = {
            0: 0.20, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.15,
            6: 0.70, 7: 0.75, 8: 0.60, 9: 0.15, 10: 0.10, 11: 0.10,
            12: 0.25, 13: 0.15, 14: 0.10, 15: 0.20, 16: 0.70, 17: 0.85,
            18: 0.85, 19: 0.70, 20: 0.50, 21: 0.40, 22: 0.30, 23: 0.15
        }
        softener_cycle = 14
        softener_offset = 5
    else:
        weekday_profile = {
            0: 1.5, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
            6: 4.0, 7: 5.0, 8: 4.0, 9: 1.5, 10: 1.5, 11: 1.5,
            12: 2.5, 13: 1.5, 14: 1.5, 15: 2.0, 16: 3.5, 17: 5.0,
            18: 6.0, 19: 6.5, 20: 8.0, 21: 6.5, 22: 3.5, 23: 1.5
        }
        weekday_activity_prob = {
            0: 0.20, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.15,
            6: 0.70, 7: 0.75, 8: 0.60, 9: 0.15, 10: 0.10, 11: 0.10,
            12: 0.25, 13: 0.15, 14: 0.10, 15: 0.15, 16: 0.50, 17: 0.65,
            18: 0.85, 19: 0.85, 20: 0.85, 21: 0.75, 22: 0.55, 23: 0.30
        }
        softener_cycle = 7
        softener_offset = 11

    weekend_profile = {
        0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
        6: 5.5, 7: 5.0, 8: 5.0, 9: 7.0, 10: 9.5, 11: 10.5,
        12: 11.0, 13: 9.5, 14: 8.5, 15: 6.0, 16: 2.5, 17: 2.5,
        18: 2.5, 19: 3.5, 20: 8.5, 21: 5.5, 22: 4.0, 23: 2.0
    }
    weekend_activity_prob = {
        0: 0.25, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.10,
        6: 0.70, 7: 0.70, 8: 0.70, 9: 0.80, 10: 0.90, 11: 0.90,
        12: 0.90, 13: 0.85, 14: 0.85, 15: 0.75, 16: 0.40, 17: 0.45,
        18: 0.50, 19: 0.60, 20: 0.85, 21: 0.70, 22: 0.60, 23: 0.30
    }

    return _to_dataframe(
        lambda: _iter_hourly(
            date_range, anchor_date, vacation_days, home_holiday_days, leak_start_dt,
            weekday_profile, weekend_profile, weekday_activity_prob, weekend_activity_prob,
            softener_cycle=softener_cycle, softener_offset=softener_offset, softener_hours=[3, 4],
            softener_volumes=(24, 40), softener_jitter=(-2, 3),
            seasonal_amplitude=0.2, noise_fraction=0.10,
        ),
        household_id, stream,
    )

def generate_family_water_consumption(
    date_range=None, start_date_str="2024-01-01", years=2, seed=42,
    household_id="family_be", vacation_probability=0.05, has_leakage_prob=0.0,
    stream=False, country="be", history_buffer_df=None
):
    date_range = _init_date_range(date_range, start_date_str, years)
    if seed is not None:
        np.random.seed(seed)

    anchor_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    vacation_days, home_holiday_days = _build_vacation_days(date_range, vacation_probability, seed, country)
    leak_start_dt = _determine_leak_start_dt(date_range, has_leakage_prob, history_buffer_df)

    if country.lower() == "nl":
        # Dutch family profile: Earlier dinner peak (17:00-18:00)
        weekday_profile = {
            0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 2.5,
            6: 8.0, 7: 25.0, 8: 14.0, 9: 3.0, 10: 2.5, 11: 2.5,
            12: 5.0, 13: 3.0, 14: 2.5, 15: 12.0, 16: 22.0, 17: 28.0,
            18: 24.0, 19: 16.0, 20: 10.0, 21: 6.0, 22: 4.0, 23: 2.0
        }
        weekday_activity_prob = {
            0: 0.25, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.20,
            6: 0.85, 7: 0.95, 8: 0.80, 9: 0.25, 10: 0.20, 11: 0.20,
            12: 0.35, 13: 0.25, 14: 0.20, 15: 0.80, 16: 0.95, 17: 0.95,
            18: 0.90, 19: 0.80, 20: 0.65, 21: 0.50, 22: 0.35, 23: 0.20
        }
        softener_cycle = 8
        softener_offset = 2
    else:
        # Belgian family profile: Later dinner peak (18:00-20:00)
        weekday_profile = {
            0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 2.5,
            6: 8.0, 7: 25.0, 8: 14.0, 9: 3.0, 10: 2.5, 11: 2.5,
            12: 5.0, 13: 3.0, 14: 2.5, 15: 10.0, 16: 16.0, 17: 24.0,
            18: 28.0, 19: 25.0, 20: 16.0, 21: 10.0, 22: 5.0, 23: 3.0
        }
        weekday_activity_prob = {
            0: 0.25, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.20,
            6: 0.85, 7: 0.95, 8: 0.80, 9: 0.25, 10: 0.20, 11: 0.20,
            12: 0.35, 13: 0.25, 14: 0.20, 15: 0.75, 16: 0.85, 17: 0.95,
            18: 0.95, 19: 0.95, 20: 0.90, 21: 0.80, 22: 0.60, 23: 0.40
        }
        softener_cycle = 4
        softener_offset = 3

    weekend_profile = {
        0: 3.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 1.5,
        6: 4.0, 7: 8.0, 8: 16.0, 9: 22.0, 10: 26.0, 11: 25.0,
        12: 24.0, 13: 20.0, 14: 18.0, 15: 16.0, 16: 18.0, 17: 20.0,
        18: 24.0, 19: 22.0, 20: 18.0, 21: 12.0, 22: 7.0, 23: 4.0
    }
    weekend_activity_prob = {
        0: 0.35, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.10,
        6: 0.50, 7: 0.75, 8: 0.90, 9: 0.95, 10: 0.95, 11: 0.95,
        12: 0.95, 13: 0.90, 14: 0.90, 15: 0.85, 16: 0.85, 17: 0.90,
        18: 0.95, 19: 0.95, 20: 0.95, 21: 0.85, 22: 0.70, 23: 0.50
    }

    return _to_dataframe(
        lambda: _iter_hourly(
            date_range, anchor_date, vacation_days, home_holiday_days, leak_start_dt,
            weekday_profile, weekend_profile, weekday_activity_prob, weekend_activity_prob,
            softener_cycle=softener_cycle, softener_offset=softener_offset, softener_hours=[2, 3],
            softener_volumes=(40, 60), softener_jitter=(-3, 4),
            seasonal_amplitude=0.25, noise_fraction=0.15,
        ),
        household_id, stream,
    )


def generate_single_water_consumption(
    date_range=None, start_date_str="2024-01-01", years=2, seed=42,
    household_id="single_be", vacation_probability=0.05, has_leakage_prob=0.0,
    stream=False, country="be", history_buffer_df=None
):
    date_range = _init_date_range(date_range, start_date_str, years)
    if seed is not None:
        np.random.seed(seed)

    anchor_date = datetime.datetime.strptime(start_date_str, "%Y-%m-%d").date()
    vacation_days, home_holiday_days = _build_vacation_days(date_range, vacation_probability, seed, country)
    leak_start_dt = _determine_leak_start_dt(date_range, has_leakage_prob, history_buffer_df)

    if country.lower() == "nl":
        # Dutch single profile: Peak water activity shifted earlier (17:00-18:30)
        weekday_profile = {
            0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
            6: 3.0, 7: 10.0, 8: 4.0, 9: 2.0, 10: 2.0, 11: 2.0,
            12: 3.0, 13: 2.0, 14: 2.0, 15: 2.0, 16: 5.0, 17: 9.0,
            18: 8.0, 19: 6.0, 20: 4.0, 21: 3.0, 22: 2.0, 23: 1.5
        }
        weekday_activity_prob = {
            0: 0.08, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.02,
            6: 0.35, 7: 0.80, 8: 0.50, 9: 0.10, 10: 0.05, 11: 0.05,
            12: 0.15, 13: 0.05, 14: 0.05, 15: 0.10, 16: 0.50, 17: 0.85,
            18: 0.80, 19: 0.60, 20: 0.40, 21: 0.30, 22: 0.20, 23: 0.10
        }
        softener_cycle = 20
        softener_offset = 10
    else:
        # Belgian single profile: Peak water activity later (18:30-20:00)
        weekday_profile = {
            0: 2.0, 1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
            6: 3.0, 7: 10.0, 8: 4.0, 9: 2.0, 10: 2.0, 11: 2.0,
            12: 3.0, 13: 2.0, 14: 2.0, 15: 2.0, 16: 3.0, 17: 6.0,
            18: 8.0, 19: 9.0, 20: 7.0, 21: 6.0, 22: 4.0, 23: 2.5
        }
        weekday_activity_prob = {
            0: 0.08, 1: 0.02, 2: 0.01, 3: 0.00, 4: 0.00, 5: 0.02,
            6: 0.35, 7: 0.80, 8: 0.50, 9: 0.10, 10: 0.05, 11: 0.05,
            12: 0.15, 13: 0.05, 14: 0.05, 15: 0.05, 16: 0.20, 17: 0.65,
            18: 0.80, 19: 0.85, 20: 0.75, 21: 0.65, 22: 0.45, 23: 0.20
        }
        softener_cycle = 12
        softener_offset = 23

    weekend_profile = {
        0: 3.0, 1: 2.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0,
        6: 2.0, 7: 2.0, 8: 4.0, 9: 7.0, 10: 10.0, 11: 9.0,
        12: 8.0, 13: 6.0, 14: 5.0, 15: 4.0, 16: 4.0, 17: 5.0,
        18: 6.0, 19: 7.0, 20: 8.0, 21: 7.0, 22: 5.0, 23: 3.0
    }
    weekend_activity_prob = {
        0: 0.15, 1: 0.08, 2: 0.02, 3: 0.00, 4: 0.00, 5: 0.01,
        6: 0.08, 7: 0.20, 8: 0.50, 9: 0.75, 10: 0.85, 11: 0.85,
        12: 0.75, 13: 0.60, 14: 0.55, 15: 0.50, 16: 0.50, 17: 0.55,
        18: 0.65, 19: 0.75, 20: 0.80, 21: 0.70, 22: 0.55, 23: 0.30
    }

    rng_absence = np.random.RandomState((seed if seed is not None else 0) + 7)
    single_daytime_off_days = {
        d.date() for d in date_range
        if d.dayofweek >= 5 and rng_absence.rand() < 0.20
    }

    def _single_absence(dt, is_weekend, hour):
        return (dt.date() in single_daytime_off_days) and (9 <= hour <= 21)

    return _to_dataframe(
        lambda: _iter_hourly(
            date_range, anchor_date, vacation_days, home_holiday_days, leak_start_dt,
            weekday_profile, weekend_profile, weekday_activity_prob, weekend_activity_prob,
            softener_cycle=softener_cycle, softener_offset=softener_offset, softener_hours=[3, 4],
            softener_volumes=(24, 40), softener_jitter=(-1, 2),
            seasonal_amplitude=0.1, noise_fraction=0.20,
            extra_absence_check=_single_absence,
        ),
        household_id, stream,
    )
