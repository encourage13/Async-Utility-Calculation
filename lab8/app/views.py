import time
import random
import requests
from concurrent import futures

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status as drf_status

CALLBACK_URL = "http://localhost:8080/api/applications/"
TOKEN = "secret_code"


executor = futures.ThreadPoolExecutor(max_workers=1)


def calculate_random_sum(pk: int) -> dict:
    """
    Отложенное вычисление: ждём 5 секунд и возвращаем случайную сумму.
    pk тут просто для передачи обратно в Go.
    """
    time.sleep(5)

    rand_sum = round(random.uniform(1000, 2500), 2)

    return {
        "id": pk,
        "sum": rand_sum,
    }


def send_sum_to_go(task: futures.Future) -> None:
    """
    Колбэк, который вызывается после завершения calculate_random_sum.
    Достаём результат и шлём его в основной сервис.
    """
    try:
        result = task.result()
    except Exception:
        # Тут можно залогировать, но для лабы можно просто выйти
        return

    app_id = result["id"]
    random_sum = result["sum"]

    url = f"{CALLBACK_URL}{app_id}/async-sum"
    payload = {
        "sum": random_sum,
        "token": TOKEN,
    }

    try:
        requests.put(url, json=payload, timeout=3)
    except Exception:
        # На лабу можно не обрабатывать, максимум print
        return


@api_view(["POST"])
def async_sum(request):
    """
    HTTP-метод асинхронного сервиса.
    Принимает pk заявки, запускает отложенное вычисление,
    сразу возвращает 200, а результат отправляет в Go.
    """
    if "pk" not in request.data:
        return Response(status=drf_status.HTTP_400_BAD_REQUEST)

    try:
        pk = int(request.data["pk"])
    except (ValueError, TypeError):
        return Response(status=drf_status.HTTP_400_BAD_REQUEST)

    # Запускаем задачу в пуле потоков
    task = executor.submit(calculate_random_sum, pk)
    task.add_done_callback(send_sum_to_go)

    # Сразу отвечаем, не дожидаясь 5 секунд
    return Response(status=drf_status.HTTP_200_OK)
