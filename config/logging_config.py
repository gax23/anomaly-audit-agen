import sys
import logging
import re
from loguru import logger
from typing import Dict, Any

def mascara_datos_sensibles(record: Dict[str, Any]) -> bool:
    """
    Enmascara datos sensibles como montos, cuentas bancarias e identificadores
    en los mensajes de registro para evitar exposición en producción.
    """
    if "message" in record:
        msg = str(record["message"])
        # Enmascarar números que parecen tarjetas de crédito o cuentas (10-16 dígitos)
        msg = re.sub(r'\b\d{10,16}\b', '****-****-****', msg)
        record["message"] = msg
    return True

def setup_logging(log_level: str = "INFO", environment: str = "production") -> None:
    """
    Configura el sistema de registro de eventos usando Loguru.
    Implementa formato estructurado JSON en producción.
    """
    # Eliminar configuraciones por defecto
    logger.remove()

    if environment.lower() == "production":
        # En producción usamos formato JSON y enmascaramiento
        logger.add(
            sys.stdout,
            format="{message}",
            filter=mascara_datos_sensibles,
            level=log_level,
            serialize=True,
            enqueue=True
        )
        
        # Rotación de archivos de log: 10 MB o cada 7 días
        logger.add(
            "logs/audit_agent_production.log",
            rotation="10 MB",
            retention="7 days",
            format="{message}",
            filter=mascara_datos_sensibles,
            level=log_level,
            serialize=True,
            enqueue=True
        )
    else:
        # En desarrollo usamos un formato legible por humanos
        formato_desarrollo = (
            "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
        logger.add(
            sys.stdout,
            format=formato_desarrollo,
            level=log_level,
            enqueue=True
        )
        logger.add(
            "logs/audit_agent_dev.log",
            rotation="10 MB",
            retention="7 days",
            format=formato_desarrollo,
            level=log_level,
            enqueue=True
        )

    # Interceptar logs del estándar logging y enviarlos a loguru
    class InterceptHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = str(record.levelno)

            frame, depth = logging.currentframe(), 2
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

    # Reemplazar handlers de bibliotecas estándar
    logging.basicConfig(handlers=[InterceptHandler()], level=0)
    for logger_name in logging.root.manager.loggerDict.keys():
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = [InterceptHandler()]
