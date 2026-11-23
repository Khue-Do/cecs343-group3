## PR #66 2026-11-22 @Khue-Do
Requested: ChatGPT. Implement Issue #20, including successful payments, failed payments, inventory updates, and payment retries.
Generated: adding three tests to the existing test_order.py for successful order creation, inventory reservation, and failed-payment inventory protection.
Claimed: The existing OrderService handles payment transactions, creates orders after successful payments, preserves inventory after failed payments, and prevents duplicate orders on successful retries.
Verified: Reviewed the existing order.py and test_order.py. Confirmed that the implementation includes SQLite transactions, payment attempt records, inventory checks, and idempotency protection. Teammate review of PR #66 identified duplication with the existing order system.
Not verified: The suggested tests have not yet been confirmed as committed or passing. Removal of duplicate files, route/API test coverage, and successful GitHub Actions execution have not been verified. 

## PR #65 2026-11-22 @Khue-Do
Requested: ChatGPT. Implement Issue #8, including order statuses, and tests for the acceptance criteria.
Generated: using the existing order.py, web_app.py, and test_order.py
Claimed: The implementation supports Pending, Canceled, Refunded, and Expired statuses and records ticket selections, totals, and transaction references.
Verified: Reviewed the existing order.py and test_order.py. Confirmed that OrderService contains methods for saving orders, retrieving order details, updating statuses, and expiring pending orders. Teammate review identified redundant files in PR #65.
Not verified: The revised tests have not been confirmed as passing. Route/API test coverage, GitHub Actions results, and removal of duplicate files still need verification.

## PR #61 2026-11-22 @vanessagarciacruz
Requested : Claude. Update test_ticket_purchaser_account.py to implement tests for acceptance criteria\
Generated : 145 lines, helper functions and a test for each criteria\
Claimed : the tests pass\
Verified : ran tests and they all pass\
Not verified : page behavior on the web app aligns with updated tests

## PR #59 2026-11-21 @Weedle203
Requested: ChatGPT Work. Generate files and tests for the event, account, order, ticket, inventory, payment-integrity, and accessibility issues; leave `app.py` and `test_app.py` unchanged.\
Generated: Added `database.py`, `event_organizer_event.py`, `order.py`, `web_app.py`, and issue-specific tests; updated `ticket.py` and `ticket_purchaser_account.py`.\
Claimed: The files implement the supplied acceptance criteria, including ticket ownership, inventory checks, and accessible web forms.\
Verified: GitHub Actions ran pytest: 38 tests passed and 1 failed. The failing test was `test_event_pages_have_semantic_landmarks_labels_and_keyboard_focus_style`.\
Not verified: The test suite is not green. The failure shows `_FORM` rendered literal placeholders instead of the form fields; the fix and a passing rerun have not yet been verified. Full WCAG 2.1 AA compliance has not been audited.[moderate]

## PR #58 2026-11-21 @llarriva
Requested : ChatGPT Work. Generate ticket.py and test_ticket.py to generate unique tickets for successful purchases.
Generated : ticket.py 61 lines. test_ticket.py 115 lines.
Claimed : the test pass
Verified : CI passes
Not verified : ran all test in codespace [moderate]

## PR #32 2026-10-21 @Khue-Do
Requested : ChatGPT Work. Generate an ASCII sequence diagram for UC-01.
Generated: ASCII sequence diagram added to docs/architecture.md
Claimed: The diagram represents the saved-order flow.
Verified: Confirmed the diagram appears in the merged file on GitHub.
Not verified: The diagram matches the implemented code. No code tests were run.

## PR #54 2026-11-15 @vanessagarciacruz
Verification debt at M2: (blocking 9)\
Requested : Claude. Change UML design diagram to Mermaid code\
Generated : 66 lines, Mermaid code for UML diagram\
Claimed : the diagram will render\
Verified : opened file in GitHub website and checked that it renders\
Not verified : the diagram shows for the entire team

## PR #51 2026-11-06 @vanessagarciacruz
Verification debt at M2: (moderate 3)\
Requested : Claude. Change UML diagrams from ASCII to Mermaid code.\
Generated : 26 lines, Mermaid code that renders in GitHub.\
Claimed : the code will render\
Verified : opened file in GitHub website and checked that it renders\
Not verified : the file renders for the entire team

## PR #42 2026-11-04 @vanessagarciacruz
Verification debt at M2: (moderate 3)\
Requested : Claude. Generate code that implements issue 9 and create a test that checks the first use case.\
Generated : 63 lines, two files: ticket_purchaser_account.py and test_ticket_purchaser_account.py.\
Claimed : the test will pass\
Verified : opened file in GitHub actions and checked that it runs\
Not verified : the test actually passes

## PR #36 2026-11-02 @llarriva
Requested : Professor Zhao provided ci-flask-pytest.yml
Generated : 0 lines generated by AI. 16 lines provided. 
Claimed : Runs pytest using Ubuntu on all pushs on our repository.
Verified : green arrow on 11-02 on main.
Not verified : [minor] past pushes to repo since ci.yml had not been implemented yet.

## PR #16  2026-09-23 @vanessagarciacruz
Requested: Claude, a pytest test for Issue 9
Generated: 20 lines, one test function
Claimed: passes when user can sign in with email and password, then takes to home page
Verified: not yet verified
Not verified: passes with status code 200

## PR #16 2026-09-23 @llarriva
Verification debt at M1: (moderate 3)
Requested : ChatGPT Work. A pytest for publishing an event as an organizer (app.py)
Generated : 72 lines. Functions with different test scenarios
Claimed : passes with 1 example event information
Verified : ran it, passes all 5 test
Not verified : that it passes with different input for event information

## PR #16 2026-09-23 @Weedle203
Requested: ChatGPT Work, generate the minimal Flask code for the slice Organizer, and a pytest file with exactly five tests, one per acceptance check.
Generated: Two python files app.py and test_app.py.
Claimed: Syntax validation passed and all five test passed through direct execution.
Not verified: Did not run. Had another member run and test.

## PR #16 2026-09-23 @Khue-Do
Requested: ChatGPT Work, a pytest test for Issue 8
Generated: 18 lines, one test function
Claimed: fails now, passes when the backend correctly stores the order and changes its status to confirmed after a successful transaction.
Verified: ran it. Fails with TypeError
Not verified: it passes after implementation

## PR #16 2026-09-23 @tlay2
Verification debt at M1: (moderate 3)
Requested: ChatGpt Work, a pytest test for issue 10
Generated: 16 Lines , one test function
Claimed: An organizer can publish event information, including title, description, date, and location.
Verified: The request succeeds with one pytest.
Not verified: Authentication, authorization, input validation, persistence after reload, editing/deleting events, and whether the event is actually visible to users.
