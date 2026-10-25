# slothlens: hướng dẫn nộp bài & học code

## 0. Hạn chót

- Hạn nộp: **25/10/2026 11:59 PM PDT = 13:59 chiều Chủ nhật 26/10 giờ Việt Nam**.
- Quy định: repo phải được **tạo và hoàn thành trong thời gian thi** (19–25/10). Bạn tạo repo mới hôm nay là hợp lệ. Nếu có commit sau hạn chót thì phải ghi chú trong README.
- Bài phải viết bằng **tiếng Anh** mới được xét giải.

## 1. Checklist nộp bài (~45 phút)

1. **Tạo repo GitHub** tên `slothlens` (public), giải nén zip rồi push:
   ```bash
   cd slothlens
   git init && git add . && git commit -m "slothlens: a sloth that eats your screenshots while you sleep"
   git branch -M master
   git remote add origin https://github.com/longphanquangminh/slothlens.git
   git push -u origin master
   ```
2. ~~Thay username~~: **đã thay sẵn** `longphanquangminh` và nhánh `master` trong bài DEV và README. Ảnh trong bài dùng link raw GitHub, nên **phải push code trước** thì ảnh mới hiện trên DEV.
3. **(Khuyến nghị) Tự chạy thử trên máy mình** để có trải nghiệm thật (mục 2). Nếu có thời gian, thêm 1–2 câu thật của bạn vào bài (ví dụ: "My own Desktop had 1,214 screenshots").
   Đếm screenshot của bạn: macOS `ls ~/Desktop | grep -ci "screen\|ảnh màn hình"`.
4. **Lên DEV**: vào trang challenge, bấm nút submit để mở template, rồi **dán toàn bộ nội dung `docs/devto-post.md`** (DEV dùng markdown + front matter như trong file).
   - Ảnh cover: upload `docs/cover.jpg` (DEV cho upload trực tiếp), hoặc để link raw GitHub như trong front matter.
   - Ảnh digest & GIF: upload `docs/digest.png`, `docs/demo.gif` vào editor DEV (nút image) rồi thay link trong bài, hoặc dùng link raw GitHub sau khi push.
   - Giữ tag `devchallenge`, `hf26challenge`.
   - Bật "AI-assisted" nếu DEV hỏi (bài đã ghi rõ ở cuối; minh bạch là an toàn nhất).
5. Bấm **Preview**, kiểm tra ảnh hiển thị, rồi **Publish** trước 13:59 Chủ nhật.
6. Sau khi đăng: share lên Twitter/LinkedIn/Discord MLH. Khi điểm giám khảo hòa nhau, bài có nhiều reaction hơn sẽ thắng.

## 2. Chạy trên máy bạn

```bash
# 1) Cài Ollama: https://ollama.com/download , rồi:
ollama pull gemma3:4b

# 2) Cài slothlens
cd slothlens
python3 -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[gates]"

# 3) Chạy thử ngay, không cần đợi nửa đêm
slothlens init
slothlens nap --now --limit 3
slothlens digest --html digest.html
slothlens find "error"
slothlens status

# 4) Chạy test (không cần model)
python -m unittest discover -s tests

# 5) Thử ngay kết quả thật của mình (DB demo đã commit sẵn, KHÔNG cần model)
SLOTHLENS_HOME=demo/.home slothlens find "com tam"
SLOTHLENS_HOME=demo/.home slothlens remember
SLOTHLENS_HOME=demo/.home slothlens digest --since 30d --no-llm --html /tmp/d.html
SLOTHLENS_HOME=demo/.home python demo/evaluate.py demo/graveyard

# 6) Chạy lại toàn bộ demo từ đầu (cần model; máy yếu mất ~1 tiếng)
rm demo/.home/sloth.db
SLOTHLENS_HOME=demo/.home slothlens nap --now
# (muốn tạo lại ảnh: pip install -e ".[demo]" && playwright install chromium && python demo/make_screenshots.py demo/graveyard)
```

Máy có GPU hoặc Apple Silicon sẽ nhanh hơn nhiều (vài giây mỗi ảnh). Bài viết cố ý dùng máy yếu để khoe chữ "slow".

## 2b. Những câu kể "ngôi thứ nhất" bạn cần đọc lại trước khi đăng

Bài viết bằng giọng của bạn. Mình đã viết sao cho không bịa trải nghiệm cá nhân cụ thể, nhưng hãy đọc lại mấy chỗ này và sửa nếu không đúng với bạn:
- "If it looks anything like mine, it's a graveyard..." / "I started opening mine, one by one": giả định Desktop của bạn nhiều screenshot. Nên đếm thật và thêm số vào (rất tăng độ chân thật).
- "half my screenshots are Vietnamese (my Mac even names them `Ảnh màn hình…`)": nếu bạn dùng Windows thì sửa thành "Windows names them..." hoặc bỏ đoạn trong ngoặc.
- "The Lazy Payoff": mô tả thói quen buổi sáng. Sẽ thật hơn nếu bạn chạy slothlens trên máy mình 1 đêm trước khi đăng.
- Mọi con số (4m16s, 13/14, 0/6, 14/16...) đều là **số thật** từ lần chạy trong sandbox 2 vCPU/4GB. Log nằm trong `demo/logs/`. Nếu chạy lại trên máy bạn, con số sẽ khác (nhanh hơn nhiều nếu có GPU/Apple Silicon); khi đó hoặc giữ nguyên và ghi "on a 2 vCPU / 4 GB test box", hoặc cập nhật số của bạn.
- "Night one / two / three / four" là cách kể chuyện; thực tế là các lượt chạy liên tiếp trong cùng một đêm. Đây là hình ảnh ẩn dụ bình thường, nhưng nếu bị hỏi thì cứ nói thật.

## 3. Vì sao idea này có cửa thắng

| Tiêu chí | slothlens đáp ứng thế nào |
| --- | --- |
| Writing quality (nặng nhất) | Hook mạnh ("Open your Desktop"), insight đáng nhớ ("a screenshot is an intention with no reminder"), cấu trúc 4 đêm với war story thật (OOM killer, model đa nghi, model khai mật khẩu, tự phát hiện mình leak test data vào prompt), có số liệu before/after, tự nêu điểm yếu, giọng văn hài, có câu chốt. |
| Theme "Slow and Steady" | Không chỉ "tự động hóa cho đỡ lười": cái chậm chính là feature. 3 phút/ảnh vẫn ổn vì chạy lúc bạn ngủ. Có "sloth rules" rõ ràng. |
| Creativity | Không ai nghĩ screenshot là to-do list. Khác hẳn mấy idea gợi ý sẵn (tóm tắt group chat, file tidier...). |
| Technical execution | Chạy thật bằng Gemma 3 local, JSON-schema constrained decoding, chống prompt injection, redact 2 lớp, FTS5, undo journal, test suite, script eval có nhãn. |
| Why open matters | Lý do cực mạnh: screenshot chứa OTP, key, số tài khoản. Gửi lên cloud chính là sự cố bảo mật. |
| Partner | Best Use of Gemma ($200): Gemma là toàn bộ "bộ não". |

## 4. Đọc code theo thứ tự này

| File | Học được gì |
| --- | --- |
| `slothlens/config.py` | dataclass config + JSON + env override; danh sách tên screenshot đa ngôn ngữ |
| `slothlens/gate.py` | kiểm tra giờ (window qua nửa đêm), pin, CPU, thời gian idle của người dùng trên 3 hệ điều hành |
| `slothlens/eyes.py` | **file quan trọng nhất**: prompt, JSON Schema, gọi Ollama `/api/chat` với ảnh base64, `normalize()` phòng thủ, `redact()` bằng regex |
| `slothlens/nap.py` | vòng lặp chính: quét file, dedupe bằng sha1, hỏi gate trước mỗi ảnh, lỗi 1 ảnh không làm hỏng cả đêm |
| `slothlens/db.py` | SQLite + FTS5 (external content table + trigger), bm25 ranking, escape query an toàn |
| `slothlens/digest.py` | xuất Markdown + HTML (thumbnail base64, ảnh nhạy cảm bị blur) |
| `slothlens/tidy.py` | đổi tên/di chuyển file có journal để `undo` |
| `tests/` | test không cần model nhờ `FakeEyes` (dependency injection) |
| `demo/` | tạo screenshot giả bằng Playwright, chấm điểm, làm GIF |

### 5 khái niệm đáng học nhất

1. **Constrained decoding**: truyền JSON Schema vào trường `format` của Ollama, model *không thể* trả về JSON sai hoặc category ngoài danh sách.
2. **Hỏi kiểu enum thay vì yes/no**: model nhỏ hay trả lời "yes" bừa. Bắt nó gọi tên *loại* bí mật (enum), và đặt trường đó *sau* `key_text` (vì grammar sinh theo thứ tự), giống như ép model "đưa bằng chứng trước, kết luận sau".
3. **mmap & OOM**: Ollama tắt mmap khi chạy CPU, nên model bị nạp hết vào RAM và bị OOM killer giết. Bật `use_mmap` để weights nằm trong page cache, kernel có thể giải phóng thay vì kill.
4. **"Model chỉ ra bí mật, rồi ta vứt câu trả lời"**: trường `secret_values` cho model chép nguyên văn bí mật; code dùng nó để xóa bí mật khỏi mọi trường khác rồi `pop()` bỏ đi, không bao giờ lưu.
5. **Đừng để dữ liệu test lọt vào prompt**: ví dụ few-shot trùng ảnh test làm điểm số ảo. Luôn grep prompt với dữ liệu test.

## 5. Câu hỏi bạn có thể bị hỏi trong comment

- *Why not just OCR?* OCR cho ra chữ, không cho ra ý định. Muốn biết "đây là việc cần làm trước thứ Sáu" thì cần một model hiểu ngữ cảnh.
- *Does it work on Windows?* Có: gate idle dùng `GetLastInputInfo`, lệnh `slothlens schedule` in sẵn câu `schtasks`.
- *HEIC from iPhone?* Chưa hỗ trợ (png/jpg/webp). Ghi vào roadmap.
- *Faster?* Có GPU/Apple Silicon thì vài giây mỗi ảnh; hoặc đổi model sang `qwen2.5vl:3b`.
