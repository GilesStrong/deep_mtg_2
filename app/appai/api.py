from ninja import Router

from appai.routes.build_deck import router as build_deck_router

router = Router()
router.add_router('/deck', build_deck_router)
