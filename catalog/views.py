from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages
from django import forms
from django.contrib.auth.models import User
from .models import Book

class CustomUserCreationForm(UserCreationForm):
    # Thêm trường email optional
    email = forms.EmailField(
        required=False, 
        label="Email (Optional)",
        help_text="Nhập email để nhận các thông báo về việc mượn trả sách sau này."
    )

    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + ('email',)

def book_list(request):
    """
    Trang chủ Catalog: Hiển thị danh sách tất cả các sách dưới dạng grid.
    """
    books = Book.objects.all()
    # Ở các dự án lớn, có thể kẹp thêm Paginator tại đây.
    return render(request, 'catalog/book_list.html', {'books': books})

def book_detail(request, pk):
    """
    Trang chi tiết của một cuốn sách (Nếu user muốn nhấn vào xem kỹ hơn).
    """
    book = get_object_or_404(Book, pk=pk)
    return render(request, 'catalog/book_detail.html', {'book': book})

def register(request):
    """
    Trang đăng ký tài khoản mới cho sinh viên/giáo viên.
    """
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Đăng nhập luôn sau khi đăng ký thành công
            login(request, user)
            messages.success(request, f'Tạo tài khoản thành công! Xin chào {user.username}.')
            return redirect('home')
        else:
            messages.error(request, 'Đăng ký thất bại. Vui lòng kiểm tra lại thông tin bên dưới.')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})
