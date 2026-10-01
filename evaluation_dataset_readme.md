# Confirmed Evaluation Dataset

This dataset contains 40 synthetic evaluation cases for the Honor of Kings AI Post-Match Review Assistant.

## Review status

- Version: `1.0`
- Review status: all 40 cases accepted by the project owner; revised cases 31-33 received explicitly authorized AI-assisted review
- AI assistance in drafting labels: disclosed

The project owner accepted the complete evaluation set and explicitly authorized direct AI-assisted review of the revised structured-input cases 31-33. AI assistance in drafting and reviewing labels remains disclosed.

## Distribution

| Abstention level | Cases | Meaning |
|---|---:|---|
| `none` | 30 | Produce a complete evidence-limited review. |
| `partial` | 6 | Review supported aspects and decline unsupported aspects. |
| `full` | 4 | Do not judge performance; explain what must be corrected. |

## Interpretation rules

1. Team-share metrics are primary; raw totals are supporting evidence.
2. Match duration must be considered when interpreting raw totals.
3. Missing values remain `null` and must never be interpreted as zero.
4. High damage taken is not automatically positive; role, deaths, participation, and context must also be considered.
5. A win does not automatically imply good individual performance, and a loss does not automatically imply poor individual performance.
6. The system must not invent positioning, skill use, objective control, or team behavior that is not represented in the input.
7. `partial` cases must still return useful analysis for supported fields.
8. `full` cases must return a clear reason and corrective action, but no performance judgment.

## Separate testing

The current simplified application accepts structured manual input only. Broader guardrail behavior is evaluated separately and is not mixed into the main comparison between the rule baseline and the RAG plus foundation-model system.
