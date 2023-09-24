from messages.log.default import USER_COMMAND, U_PREFIX

API_TRANSSCRIBE_CONNECT_ERROR = USER_COMMAND + "API Transcribe Connect error: {}"
API_DIARIZE_CONNECT_ERROR = USER_COMMAND + "API Diarize Connect error: {}"
API_URL_TRANSCRIBE_NOT_SET = USER_COMMAND + "API_URL_TRANSCRIBE not set! Bot can't transcribe audio!"
API_URL_DIARIZE_NOT_SET = USER_COMMAND + "API_URL_DIARIZE not set! Bot can't diarize audio!"

API_TRANSCRIBE_NOT_CONNECTED = U_PREFIX + "Transcribe API is not connected!"
API_DIARIZE_NOT_CONNECTED = U_PREFIX + "Diarize API is not connected!"

REQUEST_LIMIT_REACHED = U_PREFIX + "Reached max request limit!"
PROCESSING_ERROR = U_PREFIX + "Processing error: {}"

TRANSCRIBE_RESULT = U_PREFIX + "File: {}, Result: {}"
TRANSCRIBE_ERROR = U_PREFIX + "File: {}, Transcribe API error: {}"
TRANSCRIBE_SENDING_ERROR = U_PREFIX + "File: {}, Error sending result: {}"

DIARIZE_RESULT = U_PREFIX + "File: {}, Result: {}"
DIARIZE_ERROR = U_PREFIX + "File: {}, Diarize API error: {}"
DIARIZE_SENDING_ERROR = U_PREFIX + "File: {}, Error sending result: {}"
