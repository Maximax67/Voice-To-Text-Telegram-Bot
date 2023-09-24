from config import MAX_FILE_SIZE, MAX_DURATION_SECONDS

TG_FILE_SIZE_LIMIT_EXCEED = f"File size exceeds the {MAX_FILE_SIZE / (1024 * 1024):.1f} MB limit! Please send a smaller file."
TG_FILE_DURATION_LIMIT_EXCEED =f"Duration exceeds the {MAX_DURATION_SECONDS} seconds limit! Please send a shorter version!"

TG_FILE_REQUEST_ERROR = "Error requesting file data!"
TG_FILE_EXTENSION_UNKNOWN = "Unknown file extension!"
TG_FILE_UNSUPPORTED_FORMAT = "Unsupported file format: {}"

TG_FILE_WAIT_DOWNLOAD = "Downloading file..."

TG_FILE_DOWNLOAD_ERROR = "Error downloading the file!"
TG_FILE_ERROR = "Error happened!"
