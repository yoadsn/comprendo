from azure.monitor.opentelemetry import configure_azure_monitor

from comprendo.configuration import app_config

if app_config.str("APPLICATIONINSIGHTS_CONNECTION_STRING", None):
    print("Configuring Azure Monitor")
    configure_azure_monitor(logger_name="comprendo")
