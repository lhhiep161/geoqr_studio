from __future__ import annotations

import pytest

from backend.core.plus_code_parser import parse_plus_code


def test_full_plus_code_decode() -> None:
  result = parse_plus_code("7P28VMMG+6CR")
  assert result is not None
  assert -90.0 <= result.latitude <= 90.0
  assert -180.0 <= result.longitude <= 180.0


def test_short_plus_code_with_known_locality() -> None:
  result = parse_plus_code("VMMG+6CR Thới An, Hồ Chí Minh, Việt Nam")
  assert result is not None
  assert round(result.latitude, 7) == 10.8831125
  assert round(result.longitude, 7) == 106.6760156


def test_short_plus_code_without_locality_returns_error() -> None:
  with pytest.raises(ValueError):
    parse_plus_code("VMMG+6CR")


def test_invalid_plus_code_returns_error() -> None:
  with pytest.raises(ValueError):
    parse_plus_code("INVALID+CODE")
