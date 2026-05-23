# Fall Response Rules / 跌倒响应规则

## Risk Levels

Low risk:
- fall_probability < 30%
- status is safe
- action: save event log only

Medium risk:
- fall_probability between 30% and 70%
- status is warning
- action: ask the elder for confirmation and continue observation

High risk:
- fall_probability >= 70%
- status is fall
- action: trigger emergency workflow

## Emergency Workflow

When high risk is detected:

1. Ask the elder by voice:
   "A possible fall was detected. Are you okay?"

2. Wait for elder confirmation.

3. If there is no response:
   - notify family member or caregiver;
   - generate incident report;
   - save event log.

4. If there is still no confirmation:
   - escalate to community staff or emergency service.

## Privacy Rules

- Raw video should be processed locally.
- The agent should receive only structured behavior events.
- Sensitive actions require confirmation.
- Camera should be able to be turned off by the user.