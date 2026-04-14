# 📚 Hệ Thống Quản Lý Thư Viện Trực Tuyến

> **Bài tập lớn môn Lập trình Python** — Học viện Công nghệ Bưu chính Viễn thông (PTIT)

🌐 **Demo trực tuyến:** [https://danhp.pythonanywhere.com](https://danhp.pythonanywhere.com)

---

## 📋 Giới thiệu

Hệ thống quản lý thư viện trực tuyến được xây dựng bằng **Django Framework (Python)**, cho phép sinh viên tra cứu, mua và mượn sách trực tuyến. Thủ thư quản lý kho sách, xét duyệt phiếu mượn và xuất báo cáo thông qua trang Admin.

## ⚡ Tính năng chính

### 👤 Dành cho Sinh viên
- Đăng ký tài khoản với xác thực mật khẩu thời gian thực (Real-time Password Validation)
- Tra cứu sách với giao diện Grid responsive
- Giỏ hàng thông minh hỗ trợ cả **Mua** và **Mượn** sách
- Sidebar giỏ hàng trượt ngang không cần tải lại trang
- Thanh toán và tự động xuất **hóa đơn PDF** có Watermark logo PTIT

### 🛡️ Dành cho Thủ thư (Admin)
- Dashboard quản lý danh mục sách, kho sách (CRUD)
- Xét duyệt phiếu mượn sách (Pending → Approved → Returned)
- Nút **Xuất CSV** tùy chỉnh với khả năng Reactive (sáng/mờ theo tick chọn)
- Quản lý hóa đơn bán và lịch sử giao dịch

## 🛠️ Công nghệ sử dụng

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | Python 3.10 & Django 5.x |
| Frontend | HTML, Tailwind CSS |
| Database | SQLite 3 |
| PDF Engine | ReportLab |
| Hosting | PythonAnywhere |

## 📁 Cấu trúc dự án

```
library_project/
├── catalog/                  # App quản lý sách & đăng ký
│   ├── models.py             # Model: Category, Book
│   ├── views.py              # Views + CustomUserCreationForm
│   └── templates/
│       ├── base.html
│       ├── catalog/
│       └── registration/     # Login, Register
│
├── transactions/             # App giao dịch mua/mượn
│   ├── models.py             # Model: Order, OrderItem, BorrowRecord
│   ├── views.py              # Thanh toán, xuất PDF
│   ├── cart.py               # Session Cart Engine
│   ├── admin.py              # Custom Admin + CSV Export
│   └── templates/
│
├── media/                    # Ảnh bìa sách, font, logo
├── settings.py               # Cấu hình Django
├── urls.py                   # Routing
└── requirements.txt          # Dependencies
```

## 🚀 Cài đặt và Chạy

```bash
# 1. Clone repo
git clone https://github.com/tinhatinh/library_project_ptit.git
cd library_project_ptit

# 2. Tạo môi trường ảo
python -m venv env
env\Scripts\activate        # Windows
# source env/bin/activate   # Linux/Mac

# 3. Cài đặt thư viện
pip install -r requirements.txt

# 4. Tạo database
python manage.py migrate

# 5. Tạo tài khoản Admin
python manage.py createsuperuser

# 6. Chạy server
python manage.py runserver
```

Truy cập: `http://127.0.0.1:8000/` | Admin: `http://127.0.0.1:8000/admin/`

## 📸 Ảnh minh họa

> *Sẽ cập nhật sau*

## 👥 Thành viên nhóm

| STT | Họ và tên | MSSV |
|-----|-----------|------|
| 1 | | |
| 2 | | |

## 📄 Giấy phép

Dự án được thực hiện phục vụ mục đích học tập tại **Học viện Công nghệ Bưu chính Viễn thông (PTIT)**.
