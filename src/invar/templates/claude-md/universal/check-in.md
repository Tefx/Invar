## Check-In

> See [INVAR.md#check-in](./INVAR.md#check-in-required) for full protocol.

**Your first message MUST display:** `✓ Check-In: [project] | [branch] | [clean/dirty]`

**Actions:** Read `.invar/context.md`, then show status. Do NOT run guard at Check-In.

---

## Final

Your last message for an implementation task MUST display:

```
✓ Final: guard PASS | 0 errors, 2 warnings
```

{% if syntax == "mcp" -%}
Execute `invar_guard()` and show this one-line summary.
{% else -%}
Execute `invar guard` and show this one-line summary.
{% endif %}

This is your sign-out. Completes the Check-In/Final pair.
