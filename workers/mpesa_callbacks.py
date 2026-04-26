from celery import shared_task

@shared_task
def process_mpesa_callback(data):
    pass
