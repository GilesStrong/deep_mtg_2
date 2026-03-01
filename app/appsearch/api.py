from ninja import Router

from appsearch.routes.card_search import router as card_search_router

router = Router()
router.add_router('', card_search_router)
