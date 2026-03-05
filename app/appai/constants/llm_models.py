from app.app_settings import APP_SETTINGS

from appai.modules.get_model import get_model

TEXT_MODEL = get_model(model_name=APP_SETTINGS.TEXT_MODEL)
TOOL_MODEL_BASIC = get_model(model_name=APP_SETTINGS.TOOL_MODEL_BASIC)
TOOL_MODEL_THINKING = get_model(model_name=APP_SETTINGS.TOOL_MODEL_THINKING)
