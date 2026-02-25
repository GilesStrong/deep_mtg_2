from ninja import Router

from appauth.routes.token import router as token_router

router = Router()
router.add_router("", token_router)
