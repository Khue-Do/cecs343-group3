##Mermaid Diagram for UC-01 
```mermaid
flowchart LR
    TP["Ticket Purchaser"]
    S["System<br/>Records ticket selections, total, and transaction reference<br/>Records status: confirmed, pending, canceled, refunded, expired, or valid"]

    TP -- "Open saved order (user action)" --> S
    S -- "Display order details (system response)" --> TP
```

##Mermaid Sequence Diagram
```mermaid
sequenceDiagram
    participant TP as Ticket Purchaser
    participant S as System

    TP->>S: openSavedOrder()
    S->>S: recordOrder(ticketSelections, total, transactionReference)
    S->>S: recordStatus(confirmed)
    S-->>TP: displayOrder(ticketDetails, total, transactionReference, confirmed)
```
        
1.The system records the order’s ticket selections, total, and transaction reference.\
2.The system determines and records the order’s status as confirmed.\
3.The ticket purchaser opens the saved order.\
4.The system displays the ticket details, total, transaction reference, and current status.\
Extensions:\
2a. The system determines that the order is pending. It records that status and continues at step 3.\
2b. The system determines that the order is canceled. It records that status and continues at step 3.\
2c. The system determines that the order is refunded. It records that status and continues at step 3.\
2d. The system determines that the order is expired. It records that status and continues at step 3.\
2e. The system determines that the order is valid. It records that status and continues at step 3. Issue #8
