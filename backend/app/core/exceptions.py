from fastapi import Request
from fastapi.responses import JSONResponse

class HospitalBaseException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

class NotFoundException(HospitalBaseException):
    def __init__(self, detail: str = "Not Found"):
        super().__init__(status_code=404, detail=detail)

class UnauthorizedException(HospitalBaseException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)

class ForbiddenException(HospitalBaseException):
    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=403, detail=detail)

class BadRequestException(HospitalBaseException):
    def __init__(self, detail: str = "Bad Request"):
        super().__init__(status_code=400, detail=detail)

class ModelNotAvailableException(HospitalBaseException):
    def __init__(self, detail: str = "Model Not Available"):
        super().__init__(status_code=503, detail=detail)

class OCRProcessingException(HospitalBaseException):
    def __init__(self, detail: str = "OCR Processing Failed"):
        super().__init__(status_code=422, detail=detail)

class LLMServiceException(HospitalBaseException):
    def __init__(self, detail: str = "LLM Service Error"):
        super().__init__(status_code=502, detail=detail)

async def hospital_exception_handler(request: Request, exc: HospitalBaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )
