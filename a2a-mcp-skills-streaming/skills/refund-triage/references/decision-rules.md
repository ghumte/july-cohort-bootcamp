# Decision rules

These rules describe this teaching dataset, not a real merchant policy.

- A blocking policy or order finding makes the recommendation BLOCKED.
- Otherwise, a failed or missing specialist makes it INCOMPLETE.
- Only two clear findings make it READY_FOR_REVIEW.
- Record missing checks even if another finding already blocks the request.
- Model prose cannot grant approval, change the structured decision, or move money.
- Money values in the source records are whole INR for this demonstration.
