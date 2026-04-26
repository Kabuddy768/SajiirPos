import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_project.config.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # "websocket": URLRouter(
    #     some_websocket_routes
    # )
})
