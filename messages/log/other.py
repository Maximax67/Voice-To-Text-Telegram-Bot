from messages.log.default import ADMIN_COMMAND, U_PREFIX

LOGGING_WITHOUT_FILE = "LOG_FILENAME not set! Logging to the file disabled!"
TELEGRAM_TOKEN_NOT_SET = "TELEGRAM_BOT_TOKEN not set! App will crash soon..."
APP_START = "App started!"
APP_ERROR = "App Error: {}"

INVALID_MESSAGE = U_PREFIX + "Invalid message: {}"
REQUEST_LIMIT = U_PREFIX + "Max request limit exceeded!"

LONG_MESSAGE_SEND_ERROR = "Sending long message error: {}"

LOG_FILE_NOT_FOUND = ADMIN_COMMAND + "Log file not found!"
LOG_FILE_READ_ERROR = ADMIN_COMMAND + "Error getting last {} logs: {}"
