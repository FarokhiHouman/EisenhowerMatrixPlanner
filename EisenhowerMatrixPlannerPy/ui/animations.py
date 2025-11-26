# ui/animations.py
# توابع easing برای انیمیشن نرم

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_out_quad(t):
    return 1 - (1 - t) * (1 - t)