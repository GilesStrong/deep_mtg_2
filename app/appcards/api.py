from ninja import Router

from appcards.routes.card import router as card_router
from appcards.routes.deck import router as get_deck_router

router = Router()
router.add_router('/deck', get_deck_router)
router.add_router('/card', card_router)
