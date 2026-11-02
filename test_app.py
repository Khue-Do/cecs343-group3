from app import EventPublisher


def event_data(**overrides):
    data = {
        "title": "Spring Demo",
        "date": "2026-10-10",
        "time": "19:00 UTC",
        "venue": "Room 2",
        "ticket_type": "General Admission",
        "price": 25,
        "quantity": 100,
    }
    data.update(overrides)
    return data


def test_create_and_publish_an_event():
    result = EventPublisher().publish(event_data())

    assert result == {
        "message": "Event published",
        "event_page": (
            "Spring Demo\n"
            "October 10, 2026\n"
            "19:00 UTC\n"
            "Room 2\n"
            "$25\n"
            "100 tickets available"
        ),
        "public_url": "/events/spring-demo",
    }


def test_reject_an_event_without_a_title():
    publisher = EventPublisher()

    result = publisher.publish(event_data(title=""))

    assert result == {
        "message": "Enter an event title",
        "event_page": None,
        "public_url": None,
    }


def test_store_the_ticket_quantity():
    result = EventPublisher().publish(event_data(quantity=100))

    measured_number = int(result["event_page"].splitlines()[-1].split()[0])
    assert measured_number == 100


def test_show_the_event_in_the_event_list():
    publisher = EventPublisher()
    publisher.publish(event_data())

    matching_rows = [row for row in publisher.event_list() if "Spring Demo" in row]
    assert len(matching_rows) == 1


def test_prevent_publication_with_no_ticket_quantity():
    publisher = EventPublisher()

    result = publisher.publish(event_data(quantity=""))

    assert result == {
        "message": "Enter a ticket quantity",
        "event_page": None,
        "public_url": None,
    }
    assert publisher.event_list() == []
