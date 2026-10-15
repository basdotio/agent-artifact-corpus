from .meta import SingletonMeta


class ServerConfig(metaclass=SingletonMeta):
    __allowed_paths = []

    def include_allowed_paths(self, allowed_paths:list[str]):
        self.__allowed_paths.extend(allowed_paths)
    
    def allow_path(self, path:str):
        self.__allowed_paths.append(path)
    
    def get_allowed_paths(self)->list[str]:
        return self.__allowed_paths
    
    def is_allowed_path(self, path:str)->bool:
        return any(path.startswith(d) for d in self.__allowed_paths)


    
