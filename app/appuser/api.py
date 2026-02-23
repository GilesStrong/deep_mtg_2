from ninja import Router

from appuser.routes.user import router as user_router

router = Router()
router.add_router('/', user_router)
