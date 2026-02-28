---
description: Perform daily analytics review and update topic prioritization.
---

// turbo-all
1. When the user asks to "refresh analytics", "analyze channel", or "check performance" via chat:
2. Execute the autonomous analyst script via shell:
   ```bash
   /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/.venv/bin/python3 /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/agents/analyst.py
   ```
3. Report the "Winning Keywords" and "Losing Keywords" found by the analyst back to the user.
4. Confirm to the user that future pipeline runs (every 6 hours) will now automatically prioritize these winning topics.

NOTE: This script pulls real-time data from the YouTube Data API to update the prioritizer logic.

NOTE: The prioritizer agent automatically reads this JSON file to boost scores for these topics.
