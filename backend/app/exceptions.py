from __future__ import annotations


class AppException(Exception):
    def __init__(self, detail: str, status_code: int = 400, code: str = "error"):
        self.detail = detail
        self.status_code = status_code
        self.code = code


class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(detail, status_code=404, code="not_found")


class ConflictError(AppException):
    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(detail, status_code=409, code="conflict")


class ValidationError(AppException):
    def __init__(self, detail: str = "Validation failed"):
        super().__init__(detail, status_code=422, code="validation_error")
