import logging
from fastapi import FastAPI
from prometheus_fastapi_instrumentator import Instrumentator

logger = logging.getLogger(__name__)

def setup_monitoring(main_app: FastAPI, config) -> FastAPI | None:
    """
    Configure Prometheus monitoring for the FastAPI application.
    
    Returns:
        A separate FastAPI app if monitoring is on a different port, else None.
    """
    try:
        instrumentator = Instrumentator().instrument(main_app)
        
        # If same port, expose on main app
        if config.monitoring_port == config.server_port:
            instrumentator.expose(main_app, endpoint=config.monitoring_endpoint)
            logger.info(f"Prometheus monitoring enabled on main port at {config.monitoring_endpoint}")
            return None
        else:
            # Different port, create separate app
            metrics_app = FastAPI(title="X402 Metrics")
            instrumentator.expose(metrics_app, endpoint=config.monitoring_endpoint)
            logger.info(f"Prometheus monitoring prepared for separate port {config.monitoring_port} at {config.monitoring_endpoint}")
            return metrics_app
            
    except Exception as e:
        logger.error(f"Failed to initialize monitoring: {e}")
        return None
