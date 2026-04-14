from transactions.cart import Cart
from catalog.models import Book

def cart_sidebar(request):
    """
    Context Processor to inject cart summaries globally across all templates.
    Avoids doing heavy queries if cart is empty.
    """
    cart = Cart(request)
    
    buy_items = []
    buy_count = 0
    for book_id, quantity in cart.buy_cart.items():
        try:
            book = Book.objects.get(id=book_id)
            buy_items.append({
                'book': book,
                'quantity': quantity,
                'total_price': book.sell_price * quantity
            })
            buy_count += quantity
        except Book.DoesNotExist:
            pass
            
    borrow_items = []
    borrow_count = len(cart.borrow_cart)
    for book_id in cart.borrow_cart.keys():
        try:
            book = Book.objects.get(id=book_id)
            borrow_items.append({'book': book})
        except Book.DoesNotExist:
            pass
            
    return {
        'sidebar_buy_items': buy_items,
        'sidebar_borrow_items': borrow_items,
        'sidebar_buy_total': cart.get_buy_total_price(),
        'sidebar_total_count': buy_count + borrow_count
    }
