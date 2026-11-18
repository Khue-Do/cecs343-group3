

**Task sizing:** For each feature Issue, treat each line in its `## Acceptance criteria` checklist as a separate task. Each task ends in one merged PR. The longest chain below is inferred from Issue titles; check it against the acceptance criteria.

### M3

**Feature Issues:** #7, #8, #9, #10, #17, #19, #20, #21.

For **each** of those Issues:

| Task | Depends on | Longest chain |
|---|---|---|
| For one acceptance-criteria line, implement the required behavior and add the test that proves it; merge a PR that references the Issue. Repeat for each line. | Any earlier criterion task the behavior requires | #7 → #19 → #20, if confirmed by the criteria |
| Add a unit test for the Issue’s behavior; merge a PR that references the Issue. | Implementation PR(s) for that Issue | #7 → #19 → #20, if confirmed by the criteria |
| Add a route/API-level test for the Issue’s behavior; name the test level in the test file header or docstring; merge a PR that references the Issue. | Implementation PR(s) for that Issue | #7 → #19 → #20, if confirmed by the criteria |
| For an Issue still open at M3 close, move it to M4 and comment why; merge a PR recording the change if repository changes are needed. | None | |

For each AI-assisted PR merged since M2:

| Task | Depends on | Longest chain |
|---|---|---|
| Add its seven-field entry to `docs/verification-log.md`; merge a PR. | The PR being documented | |
| If the generated work is a test, verify it asserts an Issue requirement; record what the generator claimed and what was checked; merge a PR. | The test PR | |

Then complete the M3 repository and release work:

| Task | Depends on | Longest chain |
|---|---|---|
| Update `README.md`’s `## Coverage` line with the last CI run’s number and the command that produced it; merge a PR. | CI run for the updated tests | |
| Update `README.md`’s `## Verification debt` line with the weighted count and date; merge a PR. | Verification Log entries | |
| Add or update a decision record for each design change since M2; merge a PR per decision record. | The design change being recorded | |
| Ensure each closed Issue references its PR and each PR identifies its covering tests; merge a PR for any missing traceability. | Relevant feature and test PRs | |
| Create `release/0.9` from `main` and add tag `v0.9-beta`; merge a PR for any repository changes needed to prepare the release. | M3 feature, test, log, README, and decision-record tasks | |

**Longest chain (tentative):** Issue #7 criterion work → Issue #19 criterion work → Issue #20 criterion work → corresponding unit and route/API tests → M3 Coverage update → `release/0.9` and `v0.9-beta`. The title-based dependencies need confirmation from the acceptance criteria.

### M4

The prompt doesn’t include the M4 Issue titles, CD2/M3 feedback items, team member GitHub usernames, or Class 22 estimate. These tasks are still specified by the hand-in requirements:

| Task | Depends on | Longest chain |
|---|---|---|
| For each M4 Issue, split its acceptance-criteria lines into one implementation-and-test PR task per line; close the Issue by a merged PR that references it. | M4 Issue list and acceptance criteria | |
| For every M3 or M4 feature Issue, add unit and route/API-level tests if either level is missing; merge a PR per missing level. | Feature implementation PR(s) | |
| For each Issue intentionally dropped, add `wontfix`, comment with the decision record that drops it, and merge a PR if repository changes are needed. | Decision-record PR | |
| Add one decision record per design or architecture change since M2; merge a PR per record. | The design change being recorded | |
| Add one sentence per M3 feedback item to `docs/m3-response.md`, naming the change and PR number or why it was not changed; merge a PR. | M3 feedback and response PRs | |
| Add the Class 22 estimate, actual time, and one sentence explaining the difference to the bottom of `docs/m3-response.md`; merge a PR. | Estimate and actual time available | |
| Update the README opening to state what the system is, who it is for, and how to run it in that order; merge a PR. | None | |
| Update `README.md`’s `## Coverage` line with the last CI run’s number and command; merge a PR. | M4 tests and CI run | |
| Update `README.md`’s `## Verification debt` line with the weighted count and date; merge a PR. | M4 Verification Log entries | |
| Add a `v1.0` section above `v0.9-beta` in `CHANGELOG.md`; merge a PR. | M4 Issues closed | |
| Add one contribution report per member at `docs/contributions/<github-username>.md`, with the four required headings and accurate entries; merge a PR per report. | Merge history and Verification Log | |
| Ensure each AI-assisted PR since M2 has a seven-field Verification Log entry; merge a PR per missing entry. | AI-assisted PR list | |
| Ensure each team member has at least two merged PRs since M3, with teammate approval and no self-approval; merge any remaining work through reviewed PRs. | M4 work and team membership | |
| Confirm the app and test suite run in a fresh Codespace using only the README commands; merge a PR for any required fixes. | README run instructions and application changes | |
| Confirm CI is green on the `v1.0` commit and tag `v1.0`; merge any required fixes before tagging. | All release PRs and Codespace fixes | |
| Prepare the ten-minute Codespace demo at `v1.0`, with each member showing something they built and one handled failure path. | `v1.0` tag and completed features | |

**Longest chain (tentative):** M3 feedback → response and design records → M4 feature and test PRs → CI/Codespace fixes → README coverage and changelog → `v1.0` tag → demo. The requested list of M4 Issues is needed to break feature work into specific criterion-sized PR tasks.

Assignment/Owners:
M3: 
 Issues(4 task each):      Estimate:
 #7 gabriel                 3   
 #8 khue                    3
 #9 vanessa                 2
 #10 tyler                  3
 #17 leanne                 3
 #19 gabriel                2
 #20 khue                   2
 #21 tyler                  2
 Everyone edit 
 verification log  
 for their code             1

 Hours left: 21 
 Hours we have: 0
 

