from datetime import datetime


class EventPublisher:
    def __init__(self):
        self._events = {}

    def publish(self, data):
        if not data.get("title"):
            return self._rejection("Enter an event title")
        if data.get("quantity") in (None, ""):
            return self._rejection("Enter a ticket quantity")

        slug = data["title"].lower().replace(" ", "-")
        event = {
            "title": data["title"],
            "date": data["date"],
            "time": data["time"],
            "venue": data["venue"],
            "ticket_type": data["ticket_type"],
            "price": data["price"],
            "quantity": int(data["quantity"]),
        }
        self._events[slug] = event
        return {
            "message": "Event published",
            "event_page": self._render(event),
            "public_url": f"/events/{slug}",
        }

    def event_list(self):
        return [event["title"] for event in self._events.values()]

    @staticmethod
    def _rejection(message):
        return {"message": message, "event_page": None, "public_url": None}

    @staticmethod
    def _render(event):
        display_date = datetime.strptime(event["date"], "%Y-%m-%d").strftime(
            "%B %-d, %Y"
        )
        return "\n".join(
            [
                event["title"],
                display_date,
                event["time"],
                event["venue"],
                f"${event['price']}",
                f"{event['quantity']} tickets available",
            ]
        )
