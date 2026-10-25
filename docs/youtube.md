# YouTube upload info: slothlens demo

## Title

slothlens: A Sloth That Reads Your Screenshots While You Sleep (Gemma 3, 100% Local)

## Description

Your screenshots folder is a to-do list that never reminds you.

slothlens is a deliberately slow, fully local night-shift agent. After midnight, on AC power, when nobody is using the computer, it reads your screenshots one at a time with Gemma 3 4B running on your own machine through Ollama. In the morning it leaves you:

⏰ the things you screenshotted to remember, written as real to-dos
🔒 the screenshots that shouldn't still exist (OTPs, API keys, wifi passwords, account numbers)
🔎 full-text search over everything it has seen
🗂️ an optional, fully reversible tidy-up of the whole folder

No cloud. No account. No API key. Your screenshots never leave your laptop.

This demo runs on a deliberately tiny machine: 2 vCPUs, 4 GB RAM, no GPU. About 4 minutes per screenshot, which is fine, because you're asleep.

Results on a 16-screenshot labelled test set:
• Category accuracy: 14/16
• Sensitive screenshots caught: 4/4, 0 false alarms
• To-dos caught: 6/6
• Secrets that reached the database: 0/6
• Cloud bill: $0.00

🔗 Code (MIT): https://github.com/longphanquangminh/slothlens
📝 Full write-up on DEV: [paste your DEV post link here]

Built for the DEV Hacktoberfest Open-Source AI Challenge, Week 3: Slow and Steady.

#Gemma #Ollama #LocalAI #OpenSource #Hacktoberfest

## Tags

slothlens, gemma, gemma 3, ollama, local ai, local llm, open source ai, vision model, screenshots, screenshot organizer, privacy, python, cli, hacktoberfest, dev challenge, offline ai, ai agent

## Settings

- Category: Science & Technology
- Audience: No, it's not made for kids
- Thumbnail: upload docs/cover.jpg
- Visibility: Public (or Unlisted if you only want to embed it in the DEV post)
