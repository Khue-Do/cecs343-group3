1. corrected against use cases: 
+----------------------+
| order                |
+----------------------+
| ticket selections    |
| total                |
| transaction reference|
| status               |
+----------------------+
  
2. corrected against code and issues :
+-----------------------+
| TicketPurchaserAccount|
+-----------------------+
| email                 |
+-----------------------+

+-----------------------+
| EventOrganizerEvent   |
+-----------------------+
| name                  |
| date                  |
| time                  |
| venue                 |
| ticket price          |
| ticket count          |
| status                |
+-----------------------+

+-----------------------+
| Order                 |
+-----------------------+
| order reference       |
| ticket selections     |
| total                 |
| status                |
| transaction reference |
+-----------------------+

+-----------------------+
| Ticket                |
+-----------------------+
| code                  |
| venue                 |
| date                  |
| time                  |
+-----------------------+

TicketPurchaserAccount -- places ----------> Order
TicketPurchaserAccount -- owns and views --> Ticket
EventOrganizerEvent    -- saves and views --> Order
EventOrganizerEvent    -- has ------------> Ticket
Order                  -- contains -------> Ticket

3. Ranking:
Rank  File          Imports  Imported by
----  ------------  -------  -----------
1     app.py        0        1
      Imported by: test_app.py

2     test_app.py   1        0
      Imports: app.py
