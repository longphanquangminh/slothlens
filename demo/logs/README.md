# Raw logs from the real runs (2 vCPU, 4 GB RAM, no GPU, Gemma 3 4B Q4_K_M via Ollama)

| File | What happened |
| --- | --- |
| `night2_v1_yes-no-prompt.txt` | first full run, boolean `sensitive` field: 13 of 14 flagged, 2 OOM |
| `eval_v1.txt` | score of that run |
| `night3_v2_snitch_partial.txt` | enum `secret_seen`; screenshot 2 leaked the wifi password into its caption, run stopped |
| `night4_v3_contaminated_partial.txt` | `secret_values` scrub added; remember examples matched test images word for word, run stopped |
| `final_v4_night1.txt` | clean prompt, 13/16 digested, 3 OOM |
| `final_v4_night2_retry.txt` | next nap retries the failures |
| `final_v4_night3_retry.txt` | last one goes through |
| `eval_v4_final.txt` | final score, 16/16 |

(The very first attempt died on screenshot #1 from the OOM killer before mmap was enabled; its log was overwritten.)
