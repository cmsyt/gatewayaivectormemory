def error_response(error: str, details: str = "") -> dict:
    return {"success": False, "error": error, "details": details}

def success_response(**kwargs) -> dict:
    return {"success": True, **kwargs}

class AIVectorMemoryError(Exception):
    def __init__(self, error: str, details: str = ""):
        self.error = error
        self.details = details
        super().__init__(error)
