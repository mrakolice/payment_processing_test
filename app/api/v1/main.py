import fastapi

from app.api.v1.payments import views as payments_views

router = fastapi.APIRouter(prefix='/v1', tags=['v1'])

router.include_router(payments_views.router)