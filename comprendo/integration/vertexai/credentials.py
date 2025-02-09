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