from functools import wraps
from langchain_core.tools import tool, BaseTool


class ToolContextHandler:
    """
    Handles tool execution based on decorator metadata.
    - Frontend tools: Send to client for execution
    - Confirmation tools: Require user approval
    - Regular tools: Execute immediately
    """
    DECORATOR_KEY = "__decorator_key"

    # Class variable to store decorator registrations
    # Structure: {decorator_name: {function_name1, function_name2, ...}}
    _decorator_registry: dict[str, set[str]] = {}

    def __init__(self, tools: list[BaseTool]):
        self.tools_map = {t.name: self.get_actual_func(t) for t in tools}

    def has_decorator(self, tool_name: str, _decorator: callable) -> bool:
        decorator_key: str = self.get_decorator_key(_decorator)
        return tool_name in self._decorator_registry.get(decorator_key, set())

    @staticmethod
    def get_actual_func(func: BaseTool):
        while hasattr(func, "func"):
            func = func.func
        return func

    @staticmethod
    def get_decorator_key(_decorator: callable) -> str:
        try:
            return getattr(_decorator, ToolContextHandler.DECORATOR_KEY)
        except AttributeError:
            raise ValueError("Decorator passed in was not created using `tool_marker`")

    @staticmethod
    def tool_marker(attr_name: str) -> callable:
        """
        Factory that creates decorators which register a function name
        in the decorator registry without modifying the function.
        """

        def _decorator(func: callable) -> callable:
            # Get the function name
            func_name = func.__name__

            # Register this function under this decorator
            if attr_name not in ToolContextHandler._decorator_registry:
                ToolContextHandler._decorator_registry[attr_name] = set()
            ToolContextHandler._decorator_registry[attr_name].add(func_name)

            # Return the function unchanged
            return func

        setattr(_decorator, ToolContextHandler.DECORATOR_KEY, attr_name)
        return _decorator

class ToolReg:
    need_personal_data_confirmation = ToolContextHandler.tool_marker("__need_personal_data_confirmation")
    need_confirmation = ToolContextHandler.tool_marker("__need_confirmation")
    frontend_execution = ToolContextHandler.tool_marker("__frontend_execution")

if __name__ == '__main__':
    # Test with sync function
    @tool
    @ToolReg.need_personal_data_confirmation
    @ToolReg.need_confirmation
    @ToolReg.frontend_execution
    def util_sync():
        """a utility"""
        return "sync result"


    # Test with async function
    @tool
    @ToolReg.need_personal_data_confirmation
    @ToolReg.need_confirmation
    @ToolReg.frontend_execution
    async def util_async():
        """an async utility"""
        return "async result"


    def main():
        print("=== Decorator Registry ===")
        print(ToolContextHandler._decorator_registry)

        print("\n=== Using ToolContextHandler ===")
        handler = ToolContextHandler([util_sync, util_async])
        print("Sync tool has decorator:", handler.has_decorator("util_sync", ToolReg.need_personal_data_confirmation))
        print("Async tool has decorator:", handler.has_decorator("util_async", ToolReg.need_personal_data_confirmation))
        print("Sync tool needs confirmation:", handler.has_decorator("util_sync", ToolReg.need_confirmation))
        print("Async tool needs confirmation:", handler.has_decorator("util_async", ToolReg.need_confirmation))


    main()