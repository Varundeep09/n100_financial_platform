"""Unit tests for year and ticker normalisation routines (Sprint 1, Day 2)."""

from datetime import date, datetime, timezone

import numpy as np
import pandas as pd
from src.etl.loader import PARSE_ERROR, normalize_ticker, normalize_year

# ---------------------------------------------------------------------------
# normalize_year tests (Section 23 Edge Cases Table)
# ---------------------------------------------------------------------------


def test_year_mar23() -> None:
    """Verify standard 'Mar-23' format normalises to '2023-03'."""
    assert normalize_year("Mar-23") == "2023-03"


def test_year_mar_space_23() -> None:
    """Verify space-separated 'Mar 23' format normalises to '2023-03'."""
    assert normalize_year("Mar 23") == "2023-03"


def test_year_march_hyphen_2023() -> None:
    """Verify full month name 'March-2023' normalises to '2023-03'."""
    assert normalize_year("March-2023") == "2023-03"


def test_year_march_space_2023() -> None:
    """Verify full month name with space 'March 2023' normalises to '2023-03'."""
    assert normalize_year("March 2023") == "2023-03"


def test_year_march_hyphen_23() -> None:
    """Verify full month name with 2-digit year 'March-23' normalises to '2023-03'."""
    assert normalize_year("March-23") == "2023-03"


def test_year_bare_string_2023() -> None:
    """Verify bare 4-digit string year '2023' assumes March FY close '2023-03'."""
    assert normalize_year("2023") == "2023-03"


def test_year_bare_int_2023() -> None:
    """Verify bare integer year 2023 assumes March FY close '2023-03'."""
    assert normalize_year(2023) == "2023-03"


def test_year_bare_float_2023() -> None:
    """Verify bare float year 2023.0 assumes March FY close '2023-03'."""
    assert normalize_year(2023.0) == "2023-03"


def test_year_numpy_int_2024() -> None:
    """Verify numpy int64 year np.int64(2024) assumes March FY close '2024-03'."""
    assert normalize_year(np.int64(2024)) == "2024-03"


def test_year_fy23() -> None:
    """Verify 'FY23' format normalises to '2023-03'."""
    assert normalize_year("FY23") == "2023-03"


def test_year_fy_space_24() -> None:
    """Verify space-separated 'FY 24' format normalises to '2024-03'."""
    assert normalize_year("FY 24") == "2024-03"


def test_year_fy_hyphen_23() -> None:
    """Verify hyphenated 'FY-23' format normalises to '2023-03'."""
    assert normalize_year("FY-23") == "2023-03"


def test_year_fy2023() -> None:
    """Verify 4-digit 'FY2023' format normalises to '2023-03'."""
    assert normalize_year("FY2023") == "2023-03"


def test_year_fy_hyphen_2024() -> None:
    """Verify 4-digit hyphenated 'FY-2024' format normalises to '2024-03'."""
    assert normalize_year("FY-2024") == "2024-03"


def test_year_dec22() -> None:
    """Verify December year-end 'Dec-22' normalises to '2022-12'."""
    assert normalize_year("Dec-22") == "2022-12"


def test_year_dec_space_2022() -> None:
    """Verify December year-end with space 'Dec 2022' normalises to '2022-12'."""
    assert normalize_year("Dec 2022") == "2022-12"


def test_year_december_space_2023() -> None:
    """Verify full month December 'December 2023' normalises to '2023-12'."""
    assert normalize_year("December 2023") == "2023-12"


def test_year_jun23() -> None:
    """Verify June year-end 'Jun-23' normalises to '2023-06'."""
    assert normalize_year("Jun-23") == "2023-06"


def test_year_jun_space_2015() -> None:
    """Verify June year-end with space 'Jun 2015' normalises to '2015-06'."""
    assert normalize_year("Jun 2015") == "2015-06"


def test_year_june_2020() -> None:
    """Verify full month June 'June 2020' normalises to '2020-06'."""
    assert normalize_year("June 2020") == "2020-06"


def test_year_sep23() -> None:
    """Verify September year-end 'Sep-23' normalises to '2023-09'."""
    assert normalize_year("Sep-23") == "2023-09"


def test_year_sep_space_2024() -> None:
    """Verify September year-end with space 'Sep 2024' normalises to '2024-09'."""
    assert normalize_year("Sep 2024") == "2024-09"


def test_year_september_2021() -> None:
    """Verify full month September 'September 2021' normalises to '2021-09'."""
    assert normalize_year("September 2021") == "2021-09"


def test_year_already_normalized() -> None:
    """Verify already normalised string '2023-03' passes through untouched."""
    assert normalize_year("2023-03") == "2023-03"


def test_year_already_normalized_dec() -> None:
    """Verify already normalised string '2022-12' passes through untouched."""
    assert normalize_year("2022-12") == "2022-12"


def test_year_real_mar_2016_9m() -> None:
    """Verify real data transition period 'Mar 2016 9m' normalises to '2016-03'."""
    assert normalize_year("Mar 2016 9m") == "2016-03"


def test_year_real_mar_2023_15() -> None:
    """Verify real data extended period 'Mar 2023 15' normalises to '2023-03'."""
    assert normalize_year("Mar 2023 15") == "2023-03"


def test_year_datetime_obj() -> None:
    """Verify Python datetime object normalises to 'YYYY-MM'."""
    assert normalize_year(datetime(2023, 3, 31, tzinfo=timezone.utc)) == "2023-03"


def test_year_date_obj() -> None:
    """Verify Python date object normalises to 'YYYY-MM'."""
    assert normalize_year(date(2022, 12, 31)) == "2022-12"


def test_year_timestamp_obj() -> None:
    """Verify pandas Timestamp object normalises to 'YYYY-MM'."""
    assert normalize_year(pd.Timestamp("2023-06-30")) == "2023-06"


def test_year_garbage_xyz() -> None:
    """Verify garbage string 'xyz' returns PARSE_ERROR."""
    assert normalize_year("xyz") == PARSE_ERROR


def test_year_garbage_word() -> None:
    """Verify arbitrary invalid word returns PARSE_ERROR."""
    assert normalize_year("garbage_value") == PARSE_ERROR


def test_year_empty_string() -> None:
    """Verify empty string returns PARSE_ERROR."""
    assert normalize_year("") == PARSE_ERROR


def test_year_whitespace_only() -> None:
    """Verify whitespace-only string returns PARSE_ERROR."""
    assert normalize_year("   ") == PARSE_ERROR


def test_year_none() -> None:
    """Verify None input returns PARSE_ERROR."""
    assert normalize_year(None) == PARSE_ERROR


def test_year_nan() -> None:
    """Verify float NaN returns PARSE_ERROR."""
    assert normalize_year(float("nan")) == PARSE_ERROR


def test_year_invalid_numeric() -> None:
    """Verify out-of-range integer year returns PARSE_ERROR."""
    assert normalize_year(1850) == PARSE_ERROR


# ---------------------------------------------------------------------------
# normalize_ticker tests (Section 23 & DQ-08 Standards)
# ---------------------------------------------------------------------------


def test_ticker_standard() -> None:
    """Verify standard valid ticker 'TCS' returns unchanged."""
    assert normalize_ticker("TCS") == "TCS"


def test_ticker_lower() -> None:
    """Verify lowercase ticker 'tcs' converts to uppercase 'TCS'."""
    assert normalize_ticker("tcs") == "TCS"


def test_ticker_mixed_case() -> None:
    """Verify mixed case ticker 'InFy' converts to uppercase 'INFY'."""
    assert normalize_ticker("InFy") == "INFY"


def test_ticker_strip_leading() -> None:
    """Verify leading whitespace is stripped from '  TCS'."""
    assert normalize_ticker("  TCS") == "TCS"


def test_ticker_strip_trailing() -> None:
    """Verify trailing whitespace is stripped from 'TCS  '."""
    assert normalize_ticker("TCS  ") == "TCS"


def test_ticker_strip_both() -> None:
    """Verify surrounding whitespace is stripped from '  TCS  '."""
    assert normalize_ticker("  TCS  ") == "TCS"


def test_ticker_hyphen_valid() -> None:
    """Verify hyphen is preserved in valid ticker 'BAJAJ-AUTO'."""
    assert normalize_ticker("BAJAJ-AUTO") == "BAJAJ-AUTO"


def test_ticker_hyphen_lower() -> None:
    """Verify lowercase hyphenated ticker 'bajaj-auto' returns uppercase 'BAJAJ-AUTO'."""
    assert normalize_ticker("bajaj-auto") == "BAJAJ-AUTO"


def test_ticker_hyphen_whitespace() -> None:
    """Verify whitespace stripping on hyphenated ticker '  bajaj-auto  '."""
    assert normalize_ticker("  bajaj-auto  ") == "BAJAJ-AUTO"


def test_ticker_ampersand_valid() -> None:
    """Verify ampersand is preserved in valid ticker 'M&M'."""
    assert normalize_ticker("M&M") == "M&M"


def test_ticker_ampersand_lower() -> None:
    """Verify lowercase ampersand ticker 'm&m' returns uppercase 'M&M'."""
    assert normalize_ticker("m&m") == "M&M"


def test_ticker_ampersand_whitespace() -> None:
    """Verify whitespace stripping on ampersand ticker '  m&m  '."""
    assert normalize_ticker("  m&m  ") == "M&M"


def test_ticker_with_digits() -> None:
    """Verify ticker with digits '3MINDIA' is accepted."""
    assert normalize_ticker("3mindia") == "3MINDIA"


def test_ticker_hdfcbank() -> None:
    """Verify uppercase conversion for 'hdfcbank'."""
    assert normalize_ticker("hdfcbank") == "HDFCBANK"


def test_ticker_reliance() -> None:
    """Verify whitespace stripping and uppercase for '  reliance  '."""
    assert normalize_ticker("  reliance  ") == "RELIANCE"


def test_ticker_missing_none() -> None:
    """Verify None input returns None."""
    assert normalize_ticker(None) is None


def test_ticker_missing_empty() -> None:
    """Verify empty string returns None."""
    assert normalize_ticker("") is None


def test_ticker_missing_whitespace() -> None:
    """Verify whitespace-only string returns None."""
    assert normalize_ticker("    ") is None


def test_ticker_missing_nan() -> None:
    """Verify float NaN returns None."""
    assert normalize_ticker(float("nan")) is None


def test_ticker_too_short() -> None:
    """Verify single-character string 'A' is rejected as too short."""
    assert normalize_ticker("A") is None


def test_ticker_too_long() -> None:
    """Verify symbol exceeding 12 characters is rejected."""
    assert normalize_ticker("VERYLONGSYMBOLNAME") is None


def test_ticker_invalid_special_chars() -> None:
    """Verify symbol with invalid special characters is rejected."""
    assert normalize_ticker("TCS$INC") is None


def test_ticker_alias_agtl_recovers_atgl() -> None:
    """Verify raw typo 'AGTL' correctly resolves to valid master ticker 'ATGL'."""
    assert normalize_ticker("AGTL") == "ATGL"
    assert normalize_ticker(" agtl ") == "ATGL"
