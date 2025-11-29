"""
Dependency injection container.

This module provides a simple DI container for managing
service dependencies and their lifecycle.

:copyright: (c) 2025
:license: MIT
"""

import logging
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Optional,
    Type,
    TypeVar,
    Union,
    get_type_hints,
)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class Lifecycle(Enum):
    """
    Service lifecycle options.

    :cvar SINGLETON: Single instance for entire application.
    :cvar SCOPED: Single instance per scope (e.g., per request).
    :cvar TRANSIENT: New instance every time.
    """

    SINGLETON = "singleton"
    SCOPED = "scoped"
    TRANSIENT = "transient"


class ServiceDescriptor:
    """
    Describes a registered service.

    :ivar service_type: The type/interface being registered.
    :ivar factory: Factory function or class to create instance.
    :ivar lifecycle: Service lifecycle.
    :ivar instance: Cached singleton instance.
    """

    def __init__(
        self,
        service_type: Type,
        factory: Union[Type, Callable[..., Any]],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> None:
        """
        Initialize service descriptor.

        :param service_type: The type being registered.
        :type service_type: Type
        :param factory: Factory to create instances.
        :type factory: Union[Type, Callable[..., Any]]
        :param lifecycle: Service lifecycle.
        :type lifecycle: Lifecycle
        """
        self.service_type = service_type
        self.factory = factory
        self.lifecycle = lifecycle
        self.instance: Optional[Any] = None


class Container:
    """
    Dependency injection container.

    Manages service registration and resolution with support for
    different lifecycles and automatic dependency injection.

    Example::

        container = Container()


        container.register(DatabaseConnection, PostgresConnection)
        container.register(UserRepository, lifecycle=Lifecycle.SCOPED)
        container.register_instance(Config, config_instance)


        db = container.resolve(DatabaseConnection)
        repo = container.resolve(UserRepository)
    """

    def __init__(self) -> None:
        """Initialize empty container."""
        self._services: Dict[Type, ServiceDescriptor] = {}
        self._scoped_instances: Dict[str, Dict[Type, Any]] = {}

    def register(
        self,
        service_type: Type[T],
        implementation: Optional[Union[Type[T], Callable[..., T]]] = None,
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> "Container":
        """
        Register a service type.

        :param service_type: The type/interface to register.
        :type service_type: Type[T]
        :param implementation: Implementation class or factory.
        :type implementation: Optional[Union[Type[T], Callable[..., T]]]
        :param lifecycle: Service lifecycle.
        :type lifecycle: Lifecycle
        :returns: Self for chaining.
        :rtype: Container

        Example::

            container.register(IUserService, UserService)
            container.register(Config)
        """
        factory = implementation or service_type
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            factory=factory,
            lifecycle=lifecycle,
        )
        return self

    def register_instance(
        self,
        service_type: Type[T],
        instance: T,
    ) -> "Container":
        """
        Register an existing instance as singleton.

        :param service_type: The type to register.
        :type service_type: Type[T]
        :param instance: The instance to register.
        :type instance: T
        :returns: Self for chaining.
        :rtype: Container

        Example::

            config = Config()
            container.register_instance(Config, config)
        """
        descriptor = ServiceDescriptor(
            service_type=service_type,
            factory=lambda: instance,
            lifecycle=Lifecycle.SINGLETON,
        )
        descriptor.instance = instance
        self._services[service_type] = descriptor
        return self

    def register_factory(
        self,
        service_type: Type[T],
        factory: Callable[["Container"], T],
        lifecycle: Lifecycle = Lifecycle.SINGLETON,
    ) -> "Container":
        """
        Register a factory function.

        :param service_type: The type to register.
        :type service_type: Type[T]
        :param factory: Factory function receiving container.
        :type factory: Callable[[Container], T]
        :param lifecycle: Service lifecycle.
        :type lifecycle: Lifecycle
        :returns: Self for chaining.
        :rtype: Container

        Example::

            container.register_factory(
                Database,
                lambda c: Database(c.resolve(Config).db_url)
            )
        """
        self._services[service_type] = ServiceDescriptor(
            service_type=service_type,
            factory=lambda: factory(self),
            lifecycle=lifecycle,
        )
        return self

    def resolve(
        self,
        service_type: Type[T],
        scope_id: Optional[str] = None,
    ) -> T:
        """
        Resolve a service instance.

        :param service_type: The type to resolve.
        :type service_type: Type[T]
        :param scope_id: Scope ID for scoped services.
        :type scope_id: Optional[str]
        :returns: Service instance.
        :rtype: T
        :raises KeyError: If service not registered.

        Example::

            user_service = container.resolve(IUserService)
        """
        if service_type not in self._services:
            raise KeyError(f"Service {service_type.__name__} not registered")

        descriptor = self._services[service_type]

        if descriptor.lifecycle == Lifecycle.SINGLETON:
            if descriptor.instance is None:
                descriptor.instance = self._create_instance(descriptor)
            return descriptor.instance

        if descriptor.lifecycle == Lifecycle.SCOPED:
            if scope_id is None:
                raise ValueError("Scope ID required for scoped services")
            if scope_id not in self._scoped_instances:
                self._scoped_instances[scope_id] = {}
            if service_type not in self._scoped_instances[scope_id]:
                self._scoped_instances[scope_id][service_type] = self._create_instance(
                    descriptor
                )
            return self._scoped_instances[scope_id][service_type]

        return self._create_instance(descriptor)

    def _create_instance(self, descriptor: ServiceDescriptor) -> Any:
        """
        Create a service instance.

        :param descriptor: Service descriptor.
        :type descriptor: ServiceDescriptor
        :returns: New service instance.
        :rtype: Any
        """
        factory = descriptor.factory

        if isinstance(factory, type):
            return self._create_with_injection(factory)

        return factory()

    def _create_with_injection(self, cls: Type[T]) -> T:
        """
        Create instance with constructor injection.

        :param cls: Class to instantiate.
        :type cls: Type[T]
        :returns: New instance with injected dependencies.
        :rtype: T
        """
        try:
            hints = get_type_hints(cls.__init__)
        except Exception:
            hints = {}

        hints.pop("return", None)

        kwargs = {}
        for param_name, param_type in hints.items():
            if param_type in self._services:
                kwargs[param_name] = self.resolve(param_type)

        return cls(**kwargs)

    def try_resolve(
        self,
        service_type: Type[T],
        scope_id: Optional[str] = None,
    ) -> Optional[T]:
        """
        Try to resolve a service, return None if not found.

        :param service_type: The type to resolve.
        :type service_type: Type[T]
        :param scope_id: Scope ID for scoped services.
        :type scope_id: Optional[str]
        :returns: Service instance or None.
        :rtype: Optional[T]
        """
        try:
            return self.resolve(service_type, scope_id)
        except KeyError:
            return None

    def is_registered(self, service_type: Type) -> bool:
        """
        Check if a service is registered.

        :param service_type: The type to check.
        :type service_type: Type
        :returns: True if registered.
        :rtype: bool
        """
        return service_type in self._services

    def clear_scope(self, scope_id: str) -> None:
        """
        Clear all scoped instances for a scope.

        :param scope_id: Scope ID to clear.
        :type scope_id: str
        """
        if scope_id in self._scoped_instances:
            del self._scoped_instances[scope_id]

    def clear(self) -> None:
        """Clear all registrations and instances."""
        self._services.clear()
        self._scoped_instances.clear()


_container: Optional[Container] = None


def get_container() -> Container:
    """
    Get the global container instance.

    :returns: Global Container instance.
    :rtype: Container
    """
    global _container
    if _container is None:
        _container = Container()
    return _container


def configure_container(container: Container) -> None:
    """
    Set the global container instance.

    :param container: Container to use globally.
    :type container: Container
    """
    global _container
    _container = container
