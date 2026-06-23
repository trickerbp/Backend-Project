# EduMatch Resource Mapping — Backend

Backend FastAPI cho **EduMatch Resource Mapping — Hệ thống mapping khóa học
với nhu cầu học viên dựa trên tài nguyên khóa học**.

Teacher upload tài nguyên khóa học (`.pdf`, `.pptx`, `.docx`). Backend xử lý
file, trích xuất nội dung, rút trích kỹ năng/chủ đề, rồi mapping với nhu cầu
học viên. Dùng MongoDB async qua Motor, Pydantic validation, JWT auth và bcrypt
password hashing.

Role: `admin`, `teacher`, `student`.

## API endpoints

Auth:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET  /api/auth/me`

Courses (student: xem course active; teacher: CRUD course của mình; admin: tất cả):

- `GET    /api/courses`
- `GET    /api/courses/{course_id}`
- `POST   /api/courses`
- `PUT    /api/courses/{course_id}`
- `DELETE /api/courses/{course_id}`

Course resources (teacher/admin — upload `.pdf/.pptx/.docx`, process để rút trích):

- `POST   /api/courses/{course_id}/resources`
- `GET    /api/courses/{course_id}/resources`
- `GET    /api/resources/{resource_id}`
- `DELETE /api/resources/{resource_id}`
- `POST   /api/resources/{resource_id}/process`

Student profiles (student only):

- `POST /api/student-profiles`
- `GET  /api/student-profiles/me`
- `PUT  /api/student-profiles/{profile_id}`

Recommendations (student only):

- `POST /api/recommendations/generate`
- `GET  /api/recommendations/me`

## 1. MongoDB setup (Atlas)

1. Tạo MongoDB Atlas cluster.
2. Lấy connection string (Atlas → Connect → Drivers).
3. Tạo file `.env` từ template:

   ```bash
   copy .env.example .env   # Windows
   # cp .env.example .env    # macOS/Linux
   ```

4. Set giá trị trong `.env`:

   ```env
   MONGODB_URL=mongodb+srv://<username>:<password>@<cluster-url>/?retryWrites=true&w=majority
   MONGODB_DB_NAME=edumatch_resource_db
   ```

`MONGODB_DB_NAME` luôn được đọc từ env — không hard-code tên database trong code.
File `.env` không được commit (đã có trong `.gitignore`); chỉ commit `.env.example`.

## 2. Cleanup database cũ

Database cũ có thể xóa nếu không còn dùng:

```text
class_enroll_db
edumatch_db
learning_mapping_db
student_db
student_management
```

KHÔNG xóa database hệ thống của MongoDB:

```text
admin
local
config
```

`sample_mflix` là sample database của MongoDB và cleanup sẽ xóa mặc định để cluster chỉ còn dữ liệu đề tài.

Chạy cleanup bằng mongosh (cần xác nhận danh sách trước khi chạy):

```bash
mongosh "<ATLAS_CONNECTION_STRING>" scripts/mongo_cleanup.js
```

Script cleanup đang đặt `includeSampleMflix = true`.

## 3. Khởi tạo database mới + indexes

```bash
mongosh "<ATLAS_CONNECTION_STRING>" scripts/mongo_init_edumatch_resource.js
```

Script tạo database `edumatch_resource_db` với các collections: `users`,
`courses`, `course_resources`, `student_profiles`, `recommendations`,
`processing_logs` (và optional `resource_chunks`), kèm indexes cơ bản.

> Backend cũng tự tạo indexes khi khởi động (`create_indexes` trong
> `app/database/mongodb.py`) và khi chạy seed. Chạy script mongosh là tùy chọn
> nếu muốn khởi tạo trước trên Atlas.

## 4. Cài đặt & chạy backend

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

Chạy seed (tạo data mẫu, đồng thời tạo indexes):

```bash
python scripts/seed.py
```

Chạy server:

```bash
uvicorn app.main:app --reload
```

Swagger UI: `http://localhost:8000/docs`

## 5. Seed data

Script `scripts/seed.py` tạo/cập nhật (idempotent):

- 3 users:
  - `admin@gmail.com` / `123456` / `admin`
  - `teacher@gmail.com` / `123456` / `teacher`
  - `student@gmail.com` / `123456` / `student`
- 5 courses: Lập trình Web cơ bản, Cơ sở dữ liệu MongoDB, Lập trình Python
  ứng dụng, Phân tích dữ liệu với SQL, Nhập môn Machine Learning.
- 1 student profile mẫu (career goal: Frontend Developer).

Password được hash bằng bcrypt.

## 6. Kiểm tra trên MongoDB Atlas

Vào Atlas → Collections, kiểm tra database `edumatch_resource_db`:

- Collections: `users`, `courses`, `course_resources`, `student_profiles`,
  `recommendations`, `processing_logs`.
- `users`: có 3 user admin/teacher/student.
- `courses`: có 5 course.
- `student_profiles`: có ít nhất 1 profile mẫu.

Kiểm tra indexes ở tab Indexes của từng collection (ví dụ `users.email` unique,
`courses` text index trên `title`/`description`).

## 7. Biến môi trường

Xem `.env.example` để biết danh sách đầy đủ. Các biến chính:

- `MONGODB_URL`, `MONGODB_DB_NAME`
- `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_URL`
- `UPLOAD_DIR`, `MAX_UPLOAD_SIZE_MB`
- `OPENAI_API_KEY`, `USE_OPENAI_EXTRACTION`, `USE_EMBEDDING_MATCHING`
- `OPENAI_EXTRACTION_MODEL`, `OPENAI_EXTRACTION_MAX_INPUT_CHARS`,
  `OPENAI_EXTRACTION_MAX_OUTPUT_TOKENS`,
  `OPENAI_EXTRACTION_MIN_MISSING_FIELDS`,
  `OPENAI_EXTRACTION_TIMEOUT_SECONDS`
- `OPENAI_EMBEDDING_MODEL`, `OPENAI_EMBEDDING_DIMENSIONS`,
  `OPENAI_EMBEDDING_TIMEOUT_SECONDS`
- `OPENAI_EMBEDDING_MAX_INPUT_CHARS`,
  `OPENAI_EMBEDDING_SKIP_IF_LOCAL_AT_LEAST`,
  `OPENAI_EMBEDDING_SKIP_IF_LOCAL_BELOW`,
  `OPENAI_EMBEDDING_EXPAND_LOW_CONFIDENCE`

## 8. Thuật toán gợi ý khóa học

Recommender dùng luồng semantic-first:

- Học viên nhập một `intent_text` tự nhiên hoặc upload file.
- Backend rút trích intent: skill, topic, role, câu trả lời bổ sung.
- Tạo điểm semantic giữa intent và từng khóa học.
- Ghi nhận hành vi `view/select/save` để lần ranking sau có personalization.
- Lọc, xếp hạng và trả top recommendations.

Điểm tổng hợp có giải thích:

- `semantic`: trục chính, hiểu ngữ nghĩa/ngữ cảnh giữa nhu cầu và khóa học.
  Mặc định chạy local bằng taxonomy + text similarity; bật
  `USE_EMBEDDING_MATCHING=true` để dùng OpenAI embeddings nếu có
  `OPENAI_API_KEY`. Model mặc định: `text-embedding-3-small`.
- `behavior`: ưu tiên khóa học giống những môn học viên đã xem/chọn gần đây.
- `skill_gap`: kỹ năng học viên muốn học so với kỹ năng khóa học. Hỗ trợ alias
  và kỹ năng liên quan, ví dụ `trí tuệ nhân tạo` -> `AI` và liên quan đến
  `Machine Learning`, `Deep Learning`, `LLM`.
- `topic`, `goal`: so khớp lĩnh vực và mục tiêu nghề nghiệp.
- `level`, `duration`: tín hiệu phụ, có thể bỏ trống.

Response có `score_detail.semantic_match_score` và
`score_detail.behavior_match_score`.

Rút trích dữ liệu có hai tầng:

- Tầng 1: parser/OCR local + Azure Document Intelligence đọc text và rule-based
  extractor lấy field.
- Tầng 2: GPT extraction optional. Bật `USE_OPENAI_EXTRACTION=true` để dùng
  `OPENAI_EXTRACTION_MODEL` enrich JSON khi parser thiếu nhiều field.
  Mặc định model: `gpt-5.4-mini`.

Để tiết kiệm token/API:

- OpenAI extraction và embedding mặc định tắt.
- GPT extraction chỉ chạy khi thiếu ít nhất
  `OPENAI_EXTRACTION_MIN_MISSING_FIELDS` field, và chỉ gửi text rút gọn theo
  `OPENAI_EXTRACTION_MAX_INPUT_CHARS`.
- Khi bật, backend chỉ gọi OpenAI cho ca mơ hồ: local score nằm giữa
  `OPENAI_EMBEDDING_SKIP_IF_LOCAL_BELOW` và
  `OPENAI_EMBEDDING_SKIP_IF_LOCAL_AT_LEAST`.
- Không gửi raw text dài; chỉ gửi intent/tags/summary rút gọn, giới hạn bởi
  `OPENAI_EMBEDDING_MAX_INPUT_CHARS`.
- Hai đoạn cần so khớp được gửi chung trong một request và cache trong memory.
