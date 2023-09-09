from abc import ABC, abstractmethod
from aiohttp import web
from starlette.applications import Starlette
from starlette.routing import Route

class Router(ABC):
    @abstractmethod
    def add_route(self, method, path, handler):
        pass

    @abstractmethod
    async def handle_request(self, request):
        pass

class AiohttpRouter(Router):
    def __init__(self):
        self.app = web.Application()

    def add_route(self, method, path, handler):
        self.app.router.add_route(method, path, handler)

    async def handle_request(self, request):
        return await self.app.router.resolve(request).handler(request)


class ASGIRouter(Router):
    def __init__(self):
        self.app = Starlette(routes=[])

    def add_route(self, method, path, handler):
        self.app.routes.append(Route(path, handler, methods=[method]))

    async def handle_request(self, request):
        scope = request.scope
        await self.app(scope)(request.receive, request.send)
