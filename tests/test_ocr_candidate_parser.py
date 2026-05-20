from __future__ import annotations

from backend.services.ocr_service import extract_coordinate_candidates_from_text, extract_coordinate_candidates_with_warnings


def test_extract_multiple_pairs_from_table_like_text() -> None:
    text = """
    Diem X Y
    1 568262.924 1255172.51
    2 568300.125 1255200.75
    """
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) >= 2
    assert candidates[0].point_label in {"1", "Diem", "1."}
    assert abs(candidates[0].value1 - 568262.924) < 1e-6
    assert abs(candidates[0].value2 - 1255172.51) < 1e-6


def test_extract_pair_from_xy_separate_lines() -> None:
    text = """
    Moc A
    X: 568262,924
    Y: 1255172,51
    """
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) >= 1
    assert abs(candidates[0].value1 - 568262.924) < 1e-6
    assert abs(candidates[0].value2 - 1255172.51) < 1e-6


def test_extract_exact_row_pairs_without_cross_row_pairing() -> None:
    text = """
    BANG LIET KE TOA DO
    So hieu dinh thua Toa do X Y Chieu dai
    1 1203431.09 599932.66 20.00
    2 1203428.80 599912.80 4.20
    3 1203424.72 599913.81 20.00
    4 1203427.01 599933.67 4.20
    1 1203431.09 599932.66
    """
    candidates = extract_coordinate_candidates_from_text(text)
    actual = [(c.point_label, round(c.value1, 2), round(c.value2, 2), c.confidence_note) for c in candidates]
    expected = [
        ("1", 1203431.09, 599932.66, "detected from same OCR row"),
        ("2", 1203428.8, 599912.8, "detected from same OCR row"),
        ("3", 1203424.72, 599913.81, "detected from same OCR row"),
        ("4", 1203427.01, 599933.67, "detected from same OCR row"),
        ("1", 1203431.09, 599932.66, "detected from same OCR row"),
    ]
    assert actual == expected


def test_row_with_comma_decimal_is_parsed() -> None:
    text = """
    1 1203431,09 599932,66
    2 1203428,80 599912,80
    """
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) == 2
    assert round(candidates[0].value1, 2) == 1203431.09
    assert round(candidates[0].value2, 2) == 599932.66


def test_row_with_extra_length_value_keeps_first_xy_pair() -> None:
    text = "2 1203428.80 599912.80 4.20"
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) == 1
    assert round(candidates[0].value1, 2) == 1203428.80
    assert round(candidates[0].value2, 2) == 599912.80


def test_column_context_correction_case_a() -> None:
    text = """
    1 1203431.09 599932.66
    2 1203428.80 599912.80
    3 1203424.72 $99913.81
    """
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) == 3
    assert round(candidates[2].value2, 2) == 599913.81
    assert any("using column prefix 599" in c for c in candidates[2].corrections)


def test_column_context_correction_case_b() -> None:
    text = """
    1 1203431.09 699932.66
    2 1203428.80 699912.80
    3 1203424.72 $99913.81
    """
    candidates = extract_coordinate_candidates_from_text(text)
    assert len(candidates) == 3
    assert round(candidates[2].value2, 2) == 699913.81
    assert any("using column prefix 699" in c for c in candidates[2].corrections)


def test_column_context_insufficient_case_c_no_autocorrect() -> None:
    text = """
    1 1203431.09 $99913.81
    """
    candidates, warnings = extract_coordinate_candidates_with_warnings(text)
    assert len(candidates) == 0
    assert any("not enough valid column context" in w for w in warnings)


def test_strict_row_parser_pipe_sample_no_cross_row_pairs() -> None:
    text = """
    1203431.09 | 599932.66
    1203428.80 | 599912.80 | 20.00
    1203424.72 | $99913.81 anap
    1203427.01 | $99933.67 yon
    1203431.09 | $99932.66 .
    """
    candidates = extract_coordinate_candidates_from_text(text)
    actual_pairs = [(round(c.value1, 2), round(c.value2, 2)) for c in candidates]
    expected_pairs = [
        (1203431.09, 599932.66),
        (1203428.80, 599912.80),
        (1203424.72, 599913.81),
        (1203427.01, 599933.67),
        (1203431.09, 599932.66),
    ]
    assert actual_pairs == expected_pairs

    # Explicitly ensure wrong cross-row pairs are absent.
    wrong_pairs = {
        (599932.66, 1203428.80),
        (599912.80, 1203424.72),
        (99913.81, 1203427.01),
    }
    assert wrong_pairs.isdisjoint(set(actual_pairs))


def test_row_parser_recovers_missing_decimal_points_from_same_row() -> None:
    text = """
    1 120343109 59993266 20.00
    2 120342880 59991280 4.20
    3 120342472 59991381 20.00
    4 120342701 59993367 4.20
    1 120343109 59993266
    """
    candidates = extract_coordinate_candidates_from_text(text)
    actual = [(round(c.value1, 2), round(c.value2, 2)) for c in candidates]
    expected = [
        (1203431.09, 599932.66),
        (1203428.80, 599912.80),
        (1203424.72, 599913.81),
        (1203427.01, 599933.67),
        (1203431.09, 599932.66),
    ]
    assert actual == expected
    assert any("inferred decimal scale" in corr for item in candidates for corr in item.corrections)


def test_pattern_validation_filters_outlier_row() -> None:
    text = """
    1 1200033.39 591476.56
    2 1200022.35 591513.52
    3 1230002235 591514.25
    4 1200017.00 591514.06
    """
    candidates, warnings = extract_coordinate_candidates_with_warnings(text)
    actual = [(round(c.value1, 2), round(c.value2, 2)) for c in candidates]
    expected = [
        (1200033.39, 591476.56),
        (1200022.35, 591513.52),
        (1200017.00, 591514.06),
    ]
    assert actual == expected
    assert any("inconsistent coordinate pattern" in warning for warning in warnings)


def test_warns_when_line_has_digits_but_not_enough_coordinate_tokens() -> None:
    text = """
    1 1200033.39
    2 1200022.35 591513.52
    """
    candidates, warnings = extract_coordinate_candidates_with_warnings(text)
    assert len(candidates) == 1
    assert round(candidates[0].value1, 2) == 1200022.35
    assert round(candidates[0].value2, 2) == 591513.52
    assert any("not enough coordinate tokens" in warning for warning in warnings)


def test_warns_when_pipe_row_is_missing_one_side() -> None:
    text = """
    1200033.39 |
    1200022.35 | 591513.52
    """
    candidates, warnings = extract_coordinate_candidates_with_warnings(text)
    assert len(candidates) == 1
    assert round(candidates[0].value1, 2) == 1200022.35
    assert round(candidates[0].value2, 2) == 591513.52
    assert any("one side of the pair could not be read" in warning for warning in warnings)
