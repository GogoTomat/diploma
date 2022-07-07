from celery import shared_task
from django.core.mail import send_mail


@shared_task()
def new_order_email(recipient_list):
    send_mail(
        subject='Обновление статуса заказа',
        message='Заказ сформирован',
        from_email='',
        recipient_list=[recipient_list],
    )

    return None
