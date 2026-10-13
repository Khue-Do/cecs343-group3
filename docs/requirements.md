1. Purpose
   This is for event organizers and event goers. This alleviates the time cost of organizing an event and purchasing tickets for the event
2. Actors
   1. Event organizer: Publishes events with a venue, date, time, and price.
   2. Ticket Purchaser: Has a account with previous purchased tickets, and can purchase available tickets.
3. Functional
   Not written yet
   1. Event publishers can publish events. Issue #7
   2. A user can create an account with their email. Issue #9
   3. A user can purchase tickets. Issue #20
   4. After purchasing tickets, users receive identifiable ticket information. Issue #17
   5. A user can view their past and present ticket information. Issue #10

4. Quality
 1. Every completed purchase and cancellation must update ticket inventory to prevent duplicate sales and ensure customers receive their purchased tickets.
 2. Tickets must only be issued after successful payment to prevent unpaid purchases and maintain accurate ticket inventory.
 3. All customer-facing pages must meet WCAG 2.1 AA standards to ensure customers with disabilities can navigate and purchase tickets independently.
5. Out of scope
   - Event organizers will not process ticket purchases or payments though the application.
   - Users will not recell or transfer tickets through the application.
   - The application will not scan tickets or manage entry at the venue.
   - The application will not manage event cancellations or issue refunds.
6. Open questions
   - Can users purchase tickets without creating an account? Khue Do 10/12/2026
     No. Purchasers must create an account.
   - What payment methods will the application accept? Khue Do 10/12/2026
     Payments use the external payment provider; the application accepts the methods that provider supports.
   - How many tickets can a user purchase in one order? Khue Do 10/12/2026
     Limit each order to 4 tickets.
   - Can users select seats, or are seats assigned automatically? Khue Do 10/12/2026
     Seats are assigned automatically; users cannot select seats.
   - How will users receive and access purchased tickets? Khue Do 10/12/2026
     Tickets are available in the purchaser’s account, with an email confirmation.
