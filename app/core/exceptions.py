class BusinessError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(BusinessError):
    def __init__(self, resource: str, resource_id: object) -> None:
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} {resource_id} was not found",
            status_code=404,
        )

