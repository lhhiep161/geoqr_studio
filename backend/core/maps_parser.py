from __future__ import annotations

import re
from typing import Optional, Tuple
from urllib.parse import parse_qs, urlparse


_PAIR_REGEX = re.compile(r"(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)")
_AT_REGEX = re.compile(r"@(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)")
_PLACE_DATA_REGEX = re.compile(r"!3d(-?\d+(?:\.\d+)?)!4d(-?\d+(?:\.\d+)?)")

SOURCE_GOOGLE_PLACE_DATA = "google_place_data"
SOURCE_QUERY_PARAM = "query_param"
SOURCE_PLAIN_TEXT = "plain_text"
SOURCE_VIEWPORT_FALLBACK = "viewport_center_fallback"


def _validate_lat_lng(lat: float, lng: float) -> Optional[Tuple[float, float]]:
    if -90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0:
        return (lat, lng)
    return None


def parse_lat_lng_from_text(text: str) -> Optional[Tuple[float, float]]:
    parsed_with_source = parse_lat_lng_with_source(text)
    if not parsed_with_source:
        return None
    lat, lng, _source = parsed_with_source
    return (lat, lng)


def parse_lat_lng_with_source(text: str) -> Optional[Tuple[float, float, str]]:
    value = (text or "").strip()
    if not value:
        return None

    parsed = urlparse(value)
    if parsed.scheme in {"http", "https"} and parsed.netloc:
        return parse_lat_lng_from_google_maps_url_with_source(value)

    match = _PAIR_REGEX.search(value)
    if not match:
        return None
    lat = float(match.group(1))
    lng = float(match.group(2))
    valid = _validate_lat_lng(lat, lng)
    if not valid:
        return None
    return (valid[0], valid[1], SOURCE_PLAIN_TEXT)


def parse_lat_lng_from_google_maps_url(url: str) -> Optional[Tuple[float, float]]:
    parsed_with_source = parse_lat_lng_from_google_maps_url_with_source(url)
    if not parsed_with_source:
        return None
    lat, lng, _source = parsed_with_source
    return (lat, lng)


def parse_lat_lng_from_google_maps_url_with_source(url: str) -> Optional[Tuple[float, float, str]]:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return None

    full_url = parsed.geturl()
    place_match = _PLACE_DATA_REGEX.search(full_url)
    if place_match:
        lat = float(place_match.group(1))
        lng = float(place_match.group(2))
        valid = _validate_lat_lng(lat, lng)
        if valid:
            return (valid[0], valid[1], SOURCE_GOOGLE_PLACE_DATA)

    query = parse_qs(parsed.query)
    for key in ("q", "ll", "query"):
        if key in query and query[key]:
            match = _PAIR_REGEX.search(query[key][0])
            if match:
                lat = float(match.group(1))
                lng = float(match.group(2))
                valid = _validate_lat_lng(lat, lng)
                if valid:
                    return (valid[0], valid[1], SOURCE_QUERY_PARAM)

    at_match = _AT_REGEX.search(parsed.path) or _AT_REGEX.search(parsed.fragment)
    if at_match:
        lat = float(at_match.group(1))
        lng = float(at_match.group(2))
        valid = _validate_lat_lng(lat, lng)
        if valid:
            return (valid[0], valid[1], SOURCE_VIEWPORT_FALLBACK)

    return None


def is_google_maps_short_link(url: str) -> bool:
    parsed = urlparse((url or "").strip())
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower()
    return host in {"maps.app.goo.gl", "goo.gl"}
