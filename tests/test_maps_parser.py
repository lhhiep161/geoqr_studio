from __future__ import annotations

from backend.core.maps_parser import (
    SOURCE_GOOGLE_PLACE_DATA,
    is_google_maps_short_link,
    parse_lat_lng_from_google_maps_url_with_source,
    parse_lat_lng_from_text,
)


def test_parse_plain_lat_lng_comma() -> None:
    result = parse_lat_lng_from_text("10.7769,106.7009")
    assert result == (10.7769, 106.7009)


def test_parse_plain_lat_lng_space() -> None:
    result = parse_lat_lng_from_text("10.7769 106.7009")
    assert result == (10.7769, 106.7009)


def test_parse_google_maps_q_param() -> None:
    result = parse_lat_lng_from_text("https://www.google.com/maps?q=10.7769,106.7009")
    assert result == (10.7769, 106.7009)


def test_parse_google_maps_at_path() -> None:
    result = parse_lat_lng_from_text("https://www.google.com/maps/@10.7769,106.7009,17z")
    assert result == (10.7769, 106.7009)


def test_parse_shortened_maps_link_not_supported() -> None:
    result = parse_lat_lng_from_text("https://maps.app.goo.gl/xyz123")
    assert result is None


def test_detect_shortened_maps_link() -> None:
    assert is_google_maps_short_link("https://maps.app.goo.gl/xyz123") is True
    assert is_google_maps_short_link("https://goo.gl/maps/xyz123") is True


def test_place_url_priority_uses_google_place_data_url1() -> None:
    url = "https://www.google.com/maps/place/B%C3%A1nh+Trung+Thu+Nh%C6%B0+Lan/@10.7695745,106.6353224,20z/data=!4m6!3m5!1s0x31752e98c8648a6b:0x15d48c1844a0b017!8m2!3d10.7694046!4d106.635714!16s%2Fg%2F11y55wc348?entry=ttu"
    parsed = parse_lat_lng_from_google_maps_url_with_source(url)
    assert parsed is not None
    lat, lng, source = parsed
    assert lat == 10.7694046
    assert lng == 106.635714
    assert source == SOURCE_GOOGLE_PLACE_DATA


def test_place_url_priority_uses_google_place_data_url2() -> None:
    url = "https://www.google.com/maps/place/S%C3%BAp+Ba+Huy+-+%C4%90%E1%BA%A7m+Sen/@10.7695745,106.6353224,20z/data=!4m6!3m5!1s0x31752f005f55f255:0x17b37f8105ab35b!8m2!3d10.7694375!4d106.6350729!16s%2Fg%2F11xp9vs2fn?entry=ttu"
    parsed = parse_lat_lng_from_google_maps_url_with_source(url)
    assert parsed is not None
    lat, lng, source = parsed
    assert lat == 10.7694375
    assert lng == 106.6350729
    assert source == SOURCE_GOOGLE_PLACE_DATA


def test_place_url_priority_uses_google_place_data_url3() -> None:
    url = "https://www.google.com/maps/place/C%E1%BA%A7u+Ba+T%E1%BA%A5n/@10.8831063,106.6734551,17z/data=!3m1!4b1!4m6!3m5!1s0x3174d713df57a6fb:0xbdb56c33336c7862!8m2!3d10.8831063!4d106.67603!16s%2Fg%2F11fsnbp767?entry=ttu"
    parsed = parse_lat_lng_from_google_maps_url_with_source(url)
    assert parsed is not None
    lat, lng, source = parsed
    assert lat == 10.8831063
    assert lng == 106.67603
    assert source == SOURCE_GOOGLE_PLACE_DATA


def test_parse_invalid_text_returns_none() -> None:
    result = parse_lat_lng_from_text("abc xyz")
    assert result is None
