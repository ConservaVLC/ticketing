class BaseAppException(Exception):
    """Clase base para excepciones personalizadas de la aplicación."""
    pass

class DatabaseQueryError(BaseAppException):
    """Excepción para errores ocurridos durante una consulta a la base de datos."""
    def __init__(self, message="Error al ejecutar la consulta en la base de datos.", original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception

class DataProcessingError(BaseAppException):
    """Excepción para errores ocurridos durante el procesamiento de datos."""
    def __init__(self, message="Error al procesar los datos.", original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception

class InvalidDatetimeFormatError(BaseAppException):
    """Excepción para formato de fecha/hora inválido."""
    def __init__(self, message="Formato de fecha y hora inválido.", original_exception=None):
        super().__init__(message)
        self.original_exception = original_exception