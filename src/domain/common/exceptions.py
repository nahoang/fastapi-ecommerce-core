"""Domain exceptions — pure Python, zero framework or HTTP dependencies.

In Clean Architecture, business rule violations and domain errors are represented
as pure Python exceptions. They do NOT know about HTTP status codes, JSON formats,
or web frameworks (FastAPI/Starlette). The mapping to HTTP status codes is strictly
handled at the API layer.
"""


class DomainException(Exception):
    """Base exception for all domain and business logic errors.

    Attributes:
        message: Human-readable explanation of the domain error.
        error_code: Machine-readable uppercase identifier (e.g. 'ENTITY_NOT_FOUND').
    """

    def __init__(self, message: str, error_code: str | None = None) -> None:
        # Call super().__init__(message) so Python's built-in Exception stores standard error message
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class EntityNotFoundException(DomainException):
    """Raised when an entity with a specific identifier is not found in the system."""

    def __init__(self, entity_name: str, entity_id: str) -> None:
        self.entity_name = entity_name
        self.entity_id = entity_id
        message = f"{entity_name} with id '{entity_id}' not found"
        super().__init__(message=message, error_code="ENTITY_NOT_FOUND")


class DuplicateEntityException(DomainException):
    """Raised when an operation violates uniqueness constraint (e.g. slug, email, SKU)."""

    def __init__(
        self,
        message: str = "Entity with unique attribute already exists",
        error_code: str | None = "DUPLICATE_ENTITY",
    ) -> None:
        super().__init__(message=message, error_code=error_code)


class InsufficientStockException(DomainException):
    """Raised when requested inventory quantity exceeds available stock."""

    def __init__(
        self,
        message: str = "Insufficient stock available for requested quantity",
        error_code: str | None = "INSUFFICIENT_STOCK",
    ) -> None:
        super().__init__(message=message, error_code=error_code)


class InvalidOperationException(DomainException):
    """Raised when a business operation cannot be executed in the current entity state."""

    def __init__(
        self,
        message: str = "Invalid operation requested",
        error_code: str | None = "INVALID_OPERATION",
    ) -> None:
        super().__init__(message=message, error_code=error_code)
