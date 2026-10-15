# Minimal modern-di + FastMCP example.
# Run for real:  fastmcp run examples/app.py:mcp
import dataclasses

import fastmcp
from modern_di import Container, Group, Scope, providers

from modern_di_fastmcp import FromDI, setup_di


@dataclasses.dataclass(kw_only=True)
class Settings:
    greeting: str = "Hello"


@dataclasses.dataclass(kw_only=True)
class GreetingService:
    settings: Settings  # auto-injected by type

    def greet(self, name: str) -> str:
        return f"{self.settings.greeting}, {name}!"


class Dependencies(Group):
    settings = providers.Factory(scope=Scope.APP, creator=Settings)
    service = providers.Factory(scope=Scope.REQUEST, creator=GreetingService)


mcp = fastmcp.FastMCP("greeter")
container = Container(groups=[Dependencies])
setup_di(mcp, container)
container.validate()  # optional fail-fast; must come after setup_di registers its providers


@mcp.tool
def greet(name: str, service: GreetingService = FromDI(Dependencies.service)) -> str:
    return service.greet(name)
