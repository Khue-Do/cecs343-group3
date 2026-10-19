##Mermaid Diagram for UC-01 

+------------------+                           +-----------------------------------------+
| Ticket Purchaser | -- Open saved order ----> | System                                  |
|                  |    (user action)          | Records ticket selections, total, and   |
|                  |                           | transaction reference                   |
|                  |                           | Records status: confirmed, pending,     |
|                  |                           | canceled, refunded, expired, or valid   |
|                  | <--- Display order -------|                                         |
|                  |      details              |                                         |
|                  |      (system response)    |                                         |
+------------------+                           +-----------------------------------------+
