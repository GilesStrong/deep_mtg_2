from ninja import Router

from appcards.routes.get_deck import router as get_deck_router

router = Router()
router.add_router('/deck', get_deck_router)
