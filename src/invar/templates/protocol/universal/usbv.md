## USBV Workflow

**U**nderstand → **S**pecify → **B**uild → **V**alidate

| Phase | Purpose | Activities |
|-------|---------|------------|
| UNDERSTAND | Know what and why | Intent, Inspect existing code, Constraints |
| SPECIFY | Define boundaries | Preconditions, Postconditions, Examples |
| BUILD | Write code | Implement leaves, Compose |
| VALIDATE | Confirm correctness | Run verification, Review if needed |

**Key:** Inspect before Contract. Contracts before Code. Depth varies naturally.

**Review Gate:** When verification triggers `review_suggested` (escape hatches ≥3, security paths, low coverage), invoke `/review` before completion.
