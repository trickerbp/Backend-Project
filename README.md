
# ClassEnroll Mini Backend

Backend FastAPI cho đồ án **ClassEnroll Mini - Hệ thống đăng ký lớp học và
duyệt đăng ký**. API dùng MongoDB async qua Motor, Pydantic validation, JWT auth
và bcrypt password hashing.

## Cai dat

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Sua `backend/.env`:

```env
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB_NAME=class_enroll_db
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
FRONTEND_URL=http://localhost:5173
```

## Chay server

```bash
uvicorn app.main:app --reload
```

Mo Swagger UI:

```text
http://localhost:8000/docs
```

## Seed data

```bash
python scripts/seed.py
```

Script tao/cap nhat:

- Admin: `admin@gmail.com` / `123456`
- Student: `student@gmail.com` / `123456`
- 3 lớp học mẫu: Lập trình Web cơ bản, Cơ sở dữ liệu MongoDB, Nhập môn Python

## Phan quyen

- `student`: xem lớp học, đăng ký lớp, xem đăng ký của chính mình
- `admin`: thêm/sửa/xóa lớp học, xem tất cả đăng ký, duyệt/từ chối đăng ký

Tat ca route nghiep vu can header:

```http
Authorization: Bearer <access_token>
```

## Endpoints

Auth:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`

Classes:

- `GET /api/classes`
- `GET /api/classes/{class_id}`
- `POST /api/classes`
- `PUT /api/classes/{class_id}`
- `DELETE /api/classes/{class_id}`

Enrollments:

- `POST /api/enrollments`
- `GET /api/enrollments/me`
- `GET /api/enrollments`
- `PATCH /api/enrollments/{enrollment_id}/approve`
- `PATCH /api/enrollments/{enrollment_id}/reject`

## Deploy Render/Railway

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Bien moi truong can them tren cloud:

- `MONGODB_URL`
- `MONGODB_DB_NAME`
- `JWT_SECRET_KEY`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `FRONTEND_URL`
