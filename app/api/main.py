import fastapi

from app.api.v1 import main as v1_router

router=fastapi.APIRouter(prefix='/api', tags=['api'])
router.include_router(v1_router.router)

