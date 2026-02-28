---
description: How to regenerate or tweak a specific YouTube Short using cached assets
---

// turbo-all
1. Identify the story hash or approved script filename (e.g., `dc61bed19904...`).
2. (Optional) If the user wants a content tweak, edit the JSON file in `/Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/data/approved/`.
3. Execute the regeneration tool using the absolute path to the virtual environment:
   ```bash
   /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/.venv/bin/python3 /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/rerun_approved.py <story_hash_or_filename>
   ```
4. If the user explicitly requested a publish/upload, append the `--upload` flag:
   ```bash
   /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/.venv/bin/python3 /Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/rerun_approved.py <story_hash_or_filename> --upload
   ```
5. Report the location of the new MP4 file in `/Users/kinshuk.prasad/Documents/Project_X/content-generation-pipeline/data/output/`.

NOTE: This tool skips re-fetching news and re-generating expensive AI images/audio if they already exist, making it near-instant.
