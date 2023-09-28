from messages.log.default import ADMIN_COMMAND, A_PREFIX, U_PREFIX

START_COMMAND = U_PREFIX + "Used start command"
HELP_COMMAND = U_PREFIX + "Used help command"

LOGSFILE_NOT_ADMIN = A_PREFIX + "Tried to use admin logsfile command!"
LOGSFILE_NOT_SAVING = A_PREFIX + "Can't get logs file, not saving in a file"
LOGSFILE_SEND = A_PREFIX + "ALL logs sended!"
LOGSFILE_SEND_ERROR = A_PREFIX + "Can't send logs file: {}"

LOGS_NOT_ADMIN = A_PREFIX + "Tried to use admin logs command!"
LOGS_NOT_SAVING = A_PREFIX + "Can't get logs, not saving in a file"
LOGS_NO_ARGS = A_PREFIX + "Arguments not provided for logs!"
LOGS_INVALID_N = A_PREFIX + "Invalid N argument for logs: {}!"
LOGS_INVALID_N_VALUE = A_PREFIX + "Invalid N value: {}!"
LOGS_GET_ERROR = A_PREFIX + "Can't get {} lines from log file!"
LOGS_SEND = A_PREFIX + "Sended {} last lines in log file!"

FILE_NOT_ADMIN = A_PREFIX + "Tried to use admin file command!"
FILE_NOT_ARGS = A_PREFIX + "Arguments not provided for file command!"
FILE_SEND = A_PREFIX + "Sent file message: {}"
FILE_SEND_ERROR = A_PREFIX + "Error sending file: {}, Error: {}"

ADMIN_BROADCAST_NOT_ADMIN = A_PREFIX + "Tried to use admin broadcast command!"
ADMIN_BROADCAST_ONE_ADMIN = A_PREFIX + "Can't admin broadcast, only one admin!"
ADMIN_BROADCAST_NO_ARGS = A_PREFIX + "Arguments not provided for admin broadcast!"
ADMIN_BROADCAST_UNIMPORTANT = A_PREFIX + "Unimportant admin broadcast!"
ADMIN_BROADCAST_MESSAGE = A_PREFIX + "Broadcasted: {}"
ADMIN_BROADCAST_FAIL = ADMIN_COMMAND + "Message didn't broadcast to {}: {}"
ADMIN_BROADCAST_FORWARD_FAIL = ADMIN_COMMAND + "Message didn't forwarded to {}: {}"

BROADCAST_NOT_ADMIN = A_PREFIX + "Tried to use broadcast command!"
BROADCAST_NO_ARGS = A_PREFIX + "Arguments not provided for broadcast!"
BROADCAST_ID_ERROR = A_PREFIX + "Invalid broadcast ids: {}!"
BROADCAST_MESSAGE = A_PREFIX + "Broadcasted: {}"
BROADCAST_FAIL = ADMIN_COMMAND + "Message didn't broadcast to {}: {}"
BROADCAST_FORWARD_FAIL = ADMIN_COMMAND + "Message didn't forwarded to {}: {}"
