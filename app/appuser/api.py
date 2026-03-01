from ninja import Router

from appuser.routes.account import router as account_router

router = Router()
router.add_router('', account_router)
