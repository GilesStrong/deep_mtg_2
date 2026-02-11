from app.app_settings import APP_SETTINGS

from appai.modules.get_model import get_model

TEXT_MODEL = get_model(model_name=APP_SETTINGS.TEXT_MODEL)
