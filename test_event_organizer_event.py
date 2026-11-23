"""Unit tests for Issue #7 event storage and Issue #10 public event filtering."""

import sqlite3

from event_organizer_event import EventOrganizerEvent


def test_publishing_event_stores_and_formats_the_issue_7_fields():
    service = EventOrganizerEvent(sqlite3.connect(":memory:"))

    result = service.publish_event("Jazz Night", "2026-11-14", "25.00")

    assert result["message"] == "Event stored"
    assert result["event"]["name"] == "Jazz Night"
    assert result["event"]["date"] == "2026-11-14"
    assert result["event"]["ticket_price"] == 25


def test_publishing_requires_name_date_and_numeric_price():
    service = EventOrganizerEvent(sqlite3.connect(":memory:"))

    assert service.publish_event("", "2026-11-14", "25")["message"] == "Enter an event name"
    assert service.publish_event("Jazz Night", "", "25")["message"] == "Enter an event date"
    assert service.publish_event("Jazz Night", "2026-11-14", "")["message"] == "Enter a ticket price"
    assert service.publish_event("Jazz Night", "2026-11-14", "twenty-five")["message"] == "Enter a number for the ticket price"


def test_storage_error_is_reported_and_not_listed():
    db = sqlite3.connect(":memory:")
    service = EventOrganizerEvent(db)
    db.execute(
        "CREATE TRIGGER reject_event BEFORE INSERT ON events "
        "BEGIN SELECT RAISE(FAIL, 'storage unavailable'); END"
    )

    result = service.publish_event("Jazz Night", "2026-11-14", "25")

    assert result["message"] == "Event not stored"
    assert service.list_events() == []


def test_event_list_excludes_unpublished_and_filters_by_date():
    service = EventOrganizerEvent(sqlite3.connect(":memory:"))
    service.publish_event("Harbor Lights", "2026-11-14", "40", event_id="EVT-104")
    service.publish_event(
        "Hidden Event", "2026-11-14", "30", event_id="EVT-105", status="unpublished"
    )
    service.publish_event("Cedar Room", "2026-05-02", "25", event_id="EVT-052")

    assert [event["name"] for event in service.list_events(date="2026-11-14")] == ["Harbor Lights"]
    assert service.list_events(date="2026-11-15") == []
