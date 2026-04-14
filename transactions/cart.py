from decimal import Decimal
from catalog.models import Book

class Cart:
    def __init__(self, request):
        """
        Khởi tạo cart từ session. 
        Sử dụng setdefault để tạo dictionary rỗng nếu chưa tồn tại trong phiên.
        """
        self.session = request.session
        self.buy_cart = self.session.setdefault('buy_cart', {})
        self.borrow_cart = self.session.setdefault('borrow_cart', {})

    def add_to_buy(self, book, quantity=1):
        book_id = str(book.id)
        current_quantity = self.buy_cart.get(book_id, 0)
        self.buy_cart[book_id] = current_quantity + quantity
        self.save()

    def add_to_borrow(self, book):
        # Mượn 1 cuốn 1 lần nên chỉ cần gán giá trị True
        book_id = str(book.id)
        if book_id not in self.borrow_cart:
            self.borrow_cart[book_id] = True
            self.save()

    def remove_from_buy(self, book):
        book_id = str(book.id)
        if book_id in self.buy_cart:
            del self.buy_cart[book_id]
            self.save()

    def remove_from_borrow(self, book):
        book_id = str(book.id)
        if book_id in self.borrow_cart:
            del self.borrow_cart[book_id]
            self.save()

    def get_buy_total_price(self):
        # Lấy giá bán mới nhất từ database dựa trên các book_ids trong giỏ hàng
        book_ids = self.buy_cart.keys()
        books = Book.objects.filter(id__in=book_ids)
        
        # Generator expression với sum() cho cách viết Pythonic, tối ưu
        total = sum((book.sell_price * self.buy_cart[str(book.id)]) for book in books)
        return total

    def clear_buy_cart(self):
        self.session['buy_cart'] = {}
        self.buy_cart = self.session['buy_cart']
        self.save()

    def clear_borrow_cart(self):
        self.session['borrow_cart'] = {}
        self.borrow_cart = self.session['borrow_cart']
        self.save()

    def save(self):
        """
        Cờ modified = True giúp Django nhận biết dictionary bên trong section đã bị thay đổi 
        để tiến hành lưu xuống backend.
        """
        self.session.modified = True
