import json

from google.oauth2 import service_account

from comprendo.configuration import app_config


def load_google_auth_credentials():
    raw_json_dump = app_config.str("GOOGLE_APPLICATION_CREDENTIALS_JSON_DUMP", None)
    if raw_json_dump is not None:
        json_acct_info = json.loads(raw_json_dump)
        credentials = service_account.Credentials.from_service_account_info(json_acct_info)
        return credentials

    return None


def is_google_auth_configured():
    auth_from_env = app_config.str("GOOGLE_APPLICATION_CREDENTIALS", None)
    auth_from_dumped_json = app_config.str("GOOGLE_APPLICATION_CREDENTIALS_JSON_DUMP", None)
    return auth_from_env is not None or auth_from_dumped_json is not None
