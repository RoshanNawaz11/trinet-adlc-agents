# V1 — Termination Order Eligibility

## Purpose
Determine whether a service order belongs to the
WSE termination workflow.

## Required data
- case_type
- Source: Salesforce service order.

## Condition
case_type equals "Offboarding".

## Required output

### Condition matches
- eligible: true
- action: continue
- reason: The order is an Offboarding request.

### Condition does not match
- eligible: false
- action: skip
- reason: The order is outside the termination workflow.

### case_type is missing or unknown
- eligible: unknown
- action: request_missing_data
- reason: Order eligibility cannot be determined.
- Do not infer case_type from the description.

## Evidence
Return:
- Service order ID.
- case_type value used.
- Source: Salesforce service order.
- Rule ID: V1.