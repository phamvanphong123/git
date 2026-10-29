# Hệ thống đăng ký sự kiện – Công ty XYZ
Phần đã làm: **US01 – Đăng nhập & phân quyền**, **US02 – Xem danh sách, tìm kiếm/lọc sự kiện**.
Công nghệ: Python 3.10+, Flask, SQLite (file `xyz_events.db`, tự tạo ở lần chạy đầu).

## Chạy chương trình
```
python -m venv venv
venv\Scripts\activate          # macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python app.py
```
Mở http://127.0.0.1:5000. Tạo lại dữ liệu mẫu: `python db.py`. Chạy kiểm thử: `python -m unittest -v`.

## Tài khoản demo (mật khẩu:` Employee@123`)
| Email | Vai trò |
|---|---|
| employee@xyz.com | Employee → `/employee` (danh sách sự kiện) |
| organizer@xyz.com | Organizer → `/organizer` |
| admin@xyz.com | Admin → `/admin` |
| locked@xyz.com | Tài khoản bị khóa (để thử thông báo) |

## Đối chiếu tiêu chí chấp nhận
| Mục | Cách thực hiện |
|---|---|
| US01-AC1 | `templates/login.html`: email + mật khẩu |
| US01-AC2 | Sai email/mật khẩu → "Thông tin đăng nhập không chính xác" (`app.py`, `login()`) |
| US01-AC3 | Sau đăng nhập chuyển theo role: `ROLE_HOME` |
| BR08/BR09 | Decorator `role_required` kiểm tra quyền ở server; gõ thẳng URL sai quyền → 403 |
| US02-AC1 | Bảng gồm tên, thời gian, địa điểm, người tổ chức, tối đa, đã đăng ký, trạng thái |
| US02-AC2 | Lọc theo tên, khoảng ngày, phòng ban, trạng thái (`employee_home()`) |

Trạng thái sự kiện được tính khi hiển thị: Đã hủy → Đã kết thúc → Đã hết chỗ → Đã đóng đăng ký → Đang mở đăng ký.
Số "Đã đăng ký" đếm các đăng ký có trạng thái Registered/Confirmed/Attended (không tính Cancelled).

## Bảo mật đã có
Mật khẩu băm (werkzeug), truy vấn tham số hóa (chống SQL injection), CSRF token cho mọi form POST,
Jinja tự escape (chống XSS), khóa tài khoản có hiệu lực ngay cả khi đang đăng nhập.
Khi triển khai thật hãy đặt biến môi trường `SECRET_KEY`.

## Ghép với phần của thành viên khác
- `db.py`: `query()`, `query_one()`, `get_db()` dùng chung; bảng `registrations`, `events` đã có sẵn đủ cột cho US03–US08.
- Thêm route mới vào `app.py`, dùng `@role_required("Organizer", "Admin")` để phân quyền.
- Trang `/organizer`, `/admin` hiện là khung chờ để gắn US06–US08.

## Chưa làm trong phần này
US03–US08 (chi tiết, đăng ký/hủy, quản lý sự kiện, điểm danh, dashboard) thuộc thành viên khác theo bảng phân công.
