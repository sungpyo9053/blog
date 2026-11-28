# EN troubleshooting post guide v1 (11/28, owner-approved)

Full rules and evidence: editorial/operations/research/en-style-analysis.md §4 (writing 1-11, images 1-6).
1. First paragraph: the diagnosis sentence + the actual fix line. No fixed "Short answer:" label. Second sentence: environment (distro, image, command).
2. Error strings verbatim in code blocks, from real runs only.
3. Headings come from this post's symptoms; no shared skeleton ("Short answer / FAQ / Reproduce it").
4. FAQ only for real extra questions (0-4), never repeating the body; FAQPage LD = visible FAQ.
5. I for measurements, imperative for fixes, you for the reader; state what wasn't tested. Never invent a test, failure or investigation.
6. Close with a post-specific next step taken from the content.
7. Images: only things we actually ran or charted from our numbers; alt and caption written for that image (glance captions are now generated per table).
No AI-use disclosure line (owner decision). Score before scheduling:
    .venv/bin/python -m scripts.style_score EN post.html   # target >= 80
