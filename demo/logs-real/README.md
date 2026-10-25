# Raw logs: realistic screenshot set (demo/graveyard-real)

Gemma 3 4B Q4_K_M via Ollama, 2 vCPU, 4 GB RAM, no GPU, final prompt.

| File | What happened |
| --- | --- |
| `nap_1.txt` | first nap, 12 of 16 digested, 4 hit the OOM killer |
| `nap_2.txt` | retry, 3 more digested |
| `nap_3.txt` | last one goes through |
| `eval_before_fix.txt` | score as stored: `hunter2` leaked (Gemma read `@` as `6`) |
| `eval.txt` | score after the connection-string redaction fix + `slothlens rescrub` |
