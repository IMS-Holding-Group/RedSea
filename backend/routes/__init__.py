from flask import request


def body():
    """يعيد جسم الطلب JSON كقاموس، أو قاموساً فارغاً عند عدم صلاحيته."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def money(halalas):
    return round((halalas or 0) / 100, 2)
